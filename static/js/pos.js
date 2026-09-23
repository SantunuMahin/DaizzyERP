/**
 * DAIZZY POS — Interactive Cashier Engine
 * Handles hardware barcode scanner events, ZXing camera decoding, mobile touch navigation,
 * cart state, and checkout.
 * Inspired by https://www.daizzy.online
 */

class POSCartManager {
  constructor() {
    this.items = []; // [{ product, quantity, unit_price, line_total }]
    this.discountAmount = 0.00;
    this.currencySymbol = '৳';
    this.selectedPaymentMethod = 'CASH';
    this.codeReader = null;
    this.searchResults = [];
  }

  init() {
    this.bindEvents();
    this.startClock();
    this.setupMobileTabs();
    this.focusScanner();
  }

  startClock() {
    const clockEl = document.getElementById('pos-clock');
    if (!clockEl) return;
    const update = () => {
      const d = new Date();
      clockEl.textContent = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    };
    update();
    setInterval(update, 1000);
  }

  focusScanner() {
    const input = document.getElementById('barcode-input');
    if (input && window.innerWidth >= 768) {
      input.focus();
      input.select();
    }
  }

  setupMobileTabs() {
    const btnCart = document.getElementById('tab-btn-cart');
    const btnPreview = document.getElementById('tab-btn-preview');
    const previewPane = document.getElementById('pos-preview-pane');

    if (btnCart && btnPreview && previewPane) {
      btnCart.addEventListener('click', () => {
        btnCart.classList.add('active');
        btnPreview.classList.remove('active');
        previewPane.classList.remove('active-mobile-pane');
      });

      btnPreview.addEventListener('click', () => {
        btnPreview.classList.add('active');
        btnCart.classList.remove('active');
        previewPane.classList.add('active-mobile-pane');
      });
    }
  }

  playScanFeedback() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        const ctx = new AudioCtx();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(1760, ctx.currentTime); // A6 note
        gain.gain.setValueAtTime(0.2, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.12);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.12);
      }
    } catch (e) {}

    if (navigator.vibrate) {
      try {
        navigator.vibrate([40, 30, 40]);
      } catch (e) {}
    }
  }

  bindEvents() {
    const barcodeInput = document.getElementById('barcode-input');
    if (barcodeInput) {
      barcodeInput.addEventListener('keydown', async (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          const query = barcodeInput.value.trim();
          if (query) {
            await this.handleBarcodeScan(query);
            barcodeInput.value = '';
          }
        }
      });
    }

    // Global keyboard shortcuts
    window.addEventListener('keydown', (e) => {
      if (e.key === 'F2') {
        e.preventDefault();
        this.focusScanner();
      } else if (e.key === 'F4') {
        e.preventDefault();
        this.openCameraScanner();
      } else if (e.key === 'F8') {
        e.preventDefault();
        this.openPaymentModal();
      } else if (e.key === 'F9') {
        e.preventDefault();
        this.submitSale();
      } else if (e.key === 'Escape') {
        this.closeAllModals();
      }
    });

    // Clear cart button
    document.getElementById('btn-clear-cart')?.addEventListener('click', () => {
      if (this.items.length > 0 && confirm('Are you sure you want to clear the active cart?')) {
        this.clearCart();
      }
    });

    // Pay now button
    document.getElementById('btn-open-payment')?.addEventListener('click', () => {
      this.openPaymentModal();
    });

    // Confirm sale button
    document.getElementById('btn-confirm-sale')?.addEventListener('click', () => {
      this.submitSale();
    });

    // Payment method selector buttons
    document.querySelectorAll('.payment-option-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.payment-option-btn').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        this.selectedPaymentMethod = btn.dataset.method;
      });
    });

    // Amount paid input listener for live change calculation
    document.getElementById('modal-amount-paid')?.addEventListener('input', () => {
      this.recalculateChange();
    });

    // Camera scan button
    document.getElementById('btn-camera-scan')?.addEventListener('click', () => {
      this.openCameraScanner();
    });
  }

  async handleBarcodeScan(code) {
    try {
      // Fast path: lookup by exact barcode on REST API
      const res = await fetch(`/api/v1/products/barcode/${encodeURIComponent(code)}/`);
      if (res.ok) {
        const json = await res.json();
        const product = json.data;
        this.playScanFeedback();
        this.addItemToCart(product);
        this.showProductPreview(product);
        return;
      }

      // Fallback search by SKU / Name
      const searchRes = await fetch(`/api/v1/products/?search=${encodeURIComponent(code)}`);
      const searchJson = await searchRes.json();
      const results = searchJson.data || [];

      if (results.length === 1) {
        this.playScanFeedback();
        this.addItemToCart(results[0]);
        this.showProductPreview(results[0]);
      } else if (results.length > 1) {
        this.openSearchModal(results, code);
      } else {
        Toast.error(`No product found matching '${code}'`);
      }
    } catch (err) {
      console.error(err);
      Toast.error(`Scanner error: ${err.message}`);
    }
  }

  openSearchModal(products, query) {
    const modal = document.getElementById('search-modal');
    const list = document.getElementById('search-results-list');
    if (!modal || !list) return;

    list.innerHTML = products.map(p => {
      const stock = (typeof p.current_stock === 'number') ? p.current_stock : 0;
      const isOutOfStock = stock <= 0;
      const price = parseFloat(p.current_price || p.selling_price).toFixed(2);

      return `
        <div style="background: #141824; border: 1px solid rgba(255,255,255,0.08); border-radius: var(--radius-md); padding: 12px 14px; display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap;">
          <div>
            <div style="font-weight: 700; color: #FFFFFF; font-size: 0.94rem;">${p.name}</div>
            <div style="font-size: 0.76rem; color: #94A3B8; font-family: var(--font-mono); margin-top: 2px;">
              SKU: ${p.sku} · Barcode: <span style="color: #60A5FA;">${p.barcode}</span>
            </div>
          </div>
          <div style="display: flex; align-items: center; gap: 12px; margin-left: auto;">
            <div style="text-align: right;">
              <div style="font-weight: 700; color: #34D399; font-size: 1rem; font-family: var(--font-mono);">${this.currencySymbol} ${price}</div>
              <div style="font-size: 0.74rem;">
                ${isOutOfStock 
                  ? '<span style="color: #F87171; font-weight: 600;">Out of stock (0)</span>' 
                  : `<span style="color: #94A3B8;">${stock} in stock</span>`}
              </div>
            </div>
            <button type="button" class="btn btn-sm ${isOutOfStock ? 'btn-outline' : 'btn-primary'}" 
                    style="${isOutOfStock ? 'opacity: 0.4; cursor: not-allowed;' : ''}"
                    onclick="posCart.selectFromSearch(${p.id})"
                    ${isOutOfStock ? 'disabled' : ''}>
              ${isOutOfStock ? 'Empty' : '<i class="ph-bold ph-plus"></i> Add'}
            </button>
          </div>
        </div>
      `;
    }).join('');

    modal.classList.add('open');
    this.searchResults = products;
  }

  closeSearchModal() {
    document.getElementById('search-modal')?.classList.remove('open');
    this.focusScanner();
  }

  selectFromSearch(productId) {
    const product = (this.searchResults || []).find(p => p.id === productId);
    if (product) {
      this.playScanFeedback();
      this.addItemToCart(product);
      this.showProductPreview(product);
      this.closeSearchModal();
    }
  }

  addItemToCart(product) {
    const stock = (typeof product.current_stock === 'number') ? product.current_stock : 0;

    if (stock <= 0) {
      Toast.error(`"${product.name}" is OUT OF STOCK!`);
      return;
    }

    const existing = this.items.find(i => i.product.id === product.id);
    if (existing) {
      if (existing.quantity >= stock) {
        Toast.warning(`Maximum available stock reached (${stock} pcs for "${product.name}")`);
        return;
      }
      existing.quantity += 1;
      existing.line_total = (existing.quantity * existing.unit_price);
      Toast.success(`Added +1: ${product.name} (Qty: ${existing.quantity})`);
    } else {
      this.items.push({
        product: product,
        quantity: 1,
        unit_price: parseFloat(product.current_price || product.selling_price),
        line_total: parseFloat(product.current_price || product.selling_price)
      });
      Toast.success(`Added: ${product.name}`);
    }
    this.renderCart();
  }

  removeItem(productId) {
    this.items = this.items.filter(i => i.product.id !== productId);
    this.renderCart();
  }

  updateQuantity(productId, delta) {
    const item = this.items.find(i => i.product.id === productId);
    if (!item) return;

    const newQty = item.quantity + delta;
    if (newQty <= 0) {
      this.removeItem(productId);
      return;
    }
    if (item.product.current_stock && newQty > item.product.current_stock) {
      Toast.warning(`Available stock is only ${item.product.current_stock} pcs`);
      return;
    }
    item.quantity = newQty;
    item.line_total = item.quantity * item.unit_price;
    this.renderCart();
  }

  renderCart() {
    const tbody = document.getElementById('cart-items-body');
    if (!tbody) return;

    if (this.items.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align:center; color: #64748B; padding: 48px 16px;">
            <i class="ph-bold ph-shopping-bag" style="font-size: 2.2rem; display: block; margin-bottom: 8px; opacity: 0.4;"></i>
            Cart is empty. Point camera or scan barcode to add products.
          </td>
        </tr>
      `;
    } else {
      tbody.innerHTML = this.items.map((item, idx) => `
        <tr class="${idx === this.items.length - 1 ? 'active-item' : ''}">
          <td style="color: #64748B; font-size: 0.8rem;">${idx + 1}</td>
          <td>
            <div style="font-weight: 700; color: #FFFFFF;">${item.product.name}</div>
            <div style="font-size: 0.74rem; color: #94A3B8; font-family: var(--font-mono);">${item.product.barcode}</div>
          </td>
          <td style="font-family: var(--font-mono); font-weight: 600;">${this.currencySymbol} ${item.unit_price.toFixed(2)}</td>
          <td style="text-align: center;">
            <div class="qty-controls">
              <button type="button" class="qty-btn" onclick="posCart.updateQuantity(${item.product.id}, -1)">-</button>
              <span class="qty-display">${item.quantity}</span>
              <button type="button" class="qty-btn" onclick="posCart.updateQuantity(${item.product.id}, 1)">+</button>
            </div>
          </td>
          <td style="text-align: right; font-weight: 800; font-family: var(--font-mono); color: #34D399;">
            ${this.currencySymbol} ${item.line_total.toFixed(2)}
          </td>
          <td style="text-align: center;">
            <button type="button" onclick="posCart.removeItem(${item.product.id})" style="background:none; border:none; color:#EF4444; cursor:pointer; font-size:1.25rem; padding: 6px; display: inline-flex; align-items: center; justify-content: center;">
              <i class="ph-bold ph-trash"></i>
            </button>
          </td>
        </tr>
      `).join('');
    }

    // Update bottom totals & badges
    const totalQty = this.items.reduce((sum, i) => sum + i.quantity, 0);
    const subtotal = this.items.reduce((sum, i) => sum + i.line_total, 0);
    const grandTotal = Math.max(0, subtotal - this.discountAmount);

    const itemCountEl = document.getElementById('cart-item-count');
    const subtotalEl = document.getElementById('cart-subtotal');
    const grandTotalEl = document.getElementById('cart-grand-total');
    const mobileCartBadge = document.getElementById('mobile-cart-badge');

    if (itemCountEl) itemCountEl.textContent = totalQty;
    if (subtotalEl) subtotalEl.textContent = `${this.currencySymbol} ${subtotal.toFixed(2)}`;
    if (grandTotalEl) grandTotalEl.textContent = `${this.currencySymbol} ${grandTotal.toFixed(2)}`;
    if (mobileCartBadge) mobileCartBadge.textContent = totalQty;
  }

  showProductPreview(product) {
    const container = document.getElementById('preview-container');
    if (!container) return;

    container.innerHTML = `
      <div style="text-align: center; margin-bottom: 14px;">
        <div style="font-size: 1.15rem; font-weight: 800; color: #FFFFFF; font-family: var(--font-display);">${product.name}</div>
        <div style="font-size: 0.8rem; color: #94A3B8; font-family: var(--font-mono); margin-top: 2px;">
          SKU: ${product.sku} · Barcode: <span style="color: #60A5FA;">${product.barcode}</span>
        </div>
      </div>
      <div style="background: rgba(0,0,0,0.3); border-radius: var(--radius-md); padding: 16px; border: 1px solid rgba(255,255,255,0.08);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
          <span style="color: #94A3B8; font-size: 0.85rem;">Selling Price:</span>
          <span style="font-weight: 800; color: #34D399; font-size: 1.25rem; font-family: var(--font-mono);">${this.currencySymbol} ${parseFloat(product.current_price || product.selling_price).toFixed(2)}</span>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="color: #94A3B8; font-size: 0.85rem;">Current Stock:</span>
          <span style="font-weight: 700; color: #FFFFFF; font-family: var(--font-mono);">${product.current_stock || 0} ${product.unit || 'pcs'}</span>
        </div>
      </div>
    `;
  }

  openPaymentModal() {
    if (this.items.length === 0) {
      Toast.warning("Cart is empty. Scan products before proceeding to checkout.");
      return;
    }
    const subtotal = this.items.reduce((sum, i) => sum + i.line_total, 0);
    const grandTotal = Math.max(0, subtotal - this.discountAmount);

    document.getElementById('modal-payable').textContent = `${this.currencySymbol} ${grandTotal.toFixed(2)}`;
    const paidInput = document.getElementById('modal-amount-paid');
    paidInput.value = grandTotal.toFixed(2);
    this.recalculateChange();

    document.getElementById('payment-modal').classList.add('open');
    paidInput.focus();
    paidInput.select();
  }

  setExactCash() {
    const subtotal = this.items.reduce((sum, i) => sum + i.line_total, 0);
    const grandTotal = Math.max(0, subtotal - this.discountAmount);
    const paidInput = document.getElementById('modal-amount-paid');
    if (paidInput) {
      paidInput.value = grandTotal.toFixed(2);
      this.recalculateChange();
    }
  }

  addCash(amount) {
    const paidInput = document.getElementById('modal-amount-paid');
    if (paidInput) {
      const current = parseFloat(paidInput.value) || 0;
      paidInput.value = (current + amount).toFixed(2);
      this.recalculateChange();
    }
  }

  recalculateChange() {
    const subtotal = this.items.reduce((sum, i) => sum + i.line_total, 0);
    const grandTotal = Math.max(0, subtotal - this.discountAmount);
    const paid = parseFloat(document.getElementById('modal-amount-paid').value) || 0.00;
    const change = Math.max(0, paid - grandTotal);
    document.getElementById('modal-change-due').textContent = `${this.currencySymbol} ${change.toFixed(2)}`;
  }

  async submitSale() {
    if (this.items.length === 0) {
      Toast.warning("Cart is empty.");
      return;
    }

    const subtotal = this.items.reduce((sum, i) => sum + i.line_total, 0);
    const grandTotal = Math.max(0, subtotal - this.discountAmount);
    const amountPaid = parseFloat(document.getElementById('modal-amount-paid')?.value) || grandTotal;

    const payload = {
      items: this.items.map(i => ({
        product_id: i.product.id,
        quantity: i.quantity,
        unit_price: i.unit_price
      })),
      payment: {
        payment_method: this.selectedPaymentMethod,
        amount_paid: amountPaid,
      },
      customer: {
        name: document.getElementById('modal-customer-name')?.value || '',
        phone: document.getElementById('modal-customer-phone')?.value || '',
      },
      discount_amount: this.discountAmount,
      notes: "POS Retail Sale",
      idempotency_key: crypto.randomUUID()
    };

    const confirmBtn = document.getElementById('btn-confirm-sale');
    if (confirmBtn) {
      confirmBtn.disabled = true;
      confirmBtn.innerHTML = '<i class="ph-bold ph-spinner ph-spin"></i> Processing...';
    }

    try {
      const res = await fetch('/api/v1/sales/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': window.getCSRFToken(),
        },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error?.message || 'Sale checkout failed.');
      }

      Toast.success(`Sale completed: ${data.invoice_number}!`);
      this.closeAllModals();
      this.clearCart();

      // Automatically open print invoice window
      if (data.data?.id) {
        window.open(`/invoices/${data.data.id}/print/`, '_blank', 'width=450,height=700');
      }
    } catch (err) {
      console.error(err);
      Toast.error(err.message, 6000);
    } finally {
      if (confirmBtn) {
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = '<i class="ph-bold ph-check"></i> Complete Sale (F9)';
      }
    }
  }

  clearCart() {
    this.items = [];
    this.discountAmount = 0.00;
    this.renderCart();
    this.focusScanner();
  }

  // Camera Barcode Scanner via ZXing (Prioritizing Mobile Rear Camera)
  async openCameraScanner() {
    const modal = document.getElementById('camera-modal');
    if (!modal) return;
    modal.classList.add('open');

    if (!this.codeReader) {
      this.codeReader = new ZXing.BrowserMultiFormatReader();
    }

    try {
      // Find back/environment camera on phones
      const videoDevices = await this.codeReader.getVideoInputDevices();
      let targetDeviceId = null;
      if (videoDevices && videoDevices.length > 0) {
        const backCamera = videoDevices.find(dev => /back|rear|environment|primary/i.test(dev.label));
        targetDeviceId = backCamera ? backCamera.deviceId : videoDevices[videoDevices.length - 1].deviceId;
      }

      this.codeReader.decodeFromVideoDevice(targetDeviceId, 'camera-preview', (result, err) => {
        if (result) {
          const scannedText = result.getText();
          this.closeCameraModal();
          this.handleBarcodeScan(scannedText);
        }
      }).catch(err => {
        console.error(err);
        Toast.error("Camera access denied or device not supported.");
        this.closeCameraModal();
      });
    } catch (err) {
      console.error(err);
      Toast.error("Could not initialize camera scanner.");
      this.closeCameraModal();
    }
  }

  closeCameraModal() {
    document.getElementById('camera-modal')?.classList.remove('open');
    if (this.codeReader) {
      this.codeReader.reset();
    }
    this.focusScanner();
  }

  closeAllModals() {
    document.getElementById('payment-modal')?.classList.remove('open');
    this.closeCameraModal();
    this.closeSearchModal();
    this.focusScanner();
  }
}

window.posCart = new POSCartManager();
document.addEventListener('DOMContentLoaded', () => {
  window.posCart.init();
});

window.closePaymentModal = () => window.posCart.closeAllModals();
window.closeCameraModal = () => window.posCart.closeCameraModal();
window.closeSearchModal = () => window.posCart.closeSearchModal();
window.toggleFullScreen = () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(() => {});
  } else {
    document.exitFullscreen().catch(() => {});
  }
};
