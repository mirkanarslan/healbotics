/* ==========================================================================
   STRÆHN — Shop logic (products, bundles, cart, modal, nav, reveal)
   ========================================================================== */

(function () {
  "use strict";

  /* ---------- Data ---------- */

  const PRODUCTS = [
    {
      id: "shampoo",
      step: "Step 01 — Cleanse",
      name: "Heartleaf Scalp Reset Shampoo",
      size: "250 ml",
      price: 34,
      label: "Scalp Care",
      image: "./assets/shampoo.png",
      desc: "Sanfte Reinigung für Kopfhaut und Haar. Mit Heartleaf Extract, Niacinamide, Panthenol und Prebiotic Complex.",
      actives: [
        ["Heartleaf Extract", "Balance"],
        ["Niacinamide", "Scalp"],
        ["Panthenol", "Moisture"],
        ["Prebiotic Complex", "Balance"],
      ],
    },
    {
      id: "conditioner",
      step: "Step 02 — Condition",
      name: "FiberMimic Bond Repair Conditioner",
      size: "250 ml",
      price: 36,
      label: "Bond Repair",
      image: "./assets/conditioner.png",
      desc: "Pflegender Conditioner für Geschmeidigkeit, Kämmbarkeit und ein gestärktes Haargefühl. Mit Keratin Amino Acids, Hydrolyzed Rice Protein, Ceramide NP und Panthenol.",
      actives: [
        ["Keratin Amino Acids", "Strength"],
        ["Hydrolyzed Rice Protein", "Body"],
        ["Ceramide NP", "Lipids"],
        ["Panthenol", "Moisture"],
      ],
    },
    {
      id: "treatment",
      step: "Step 03 — Treat",
      name: "Liquid Lamellar Peptide Treatment",
      size: "200 ml",
      price: 42,
      label: "Hero",
      image: "./assets/treatment.png",
      desc: "Ein flüssiges Treatment für glattere Längen, mehr Glanz und ein veredeltes Haargefühl. Mit Keratin Amino Acids, Copper Tripeptide-1, Hydrolyzed Rice Protein und Panthenol.",
      actives: [
        ["Keratin Amino Acids", "Strength"],
        ["Copper Tripeptide-1", "Signal"],
        ["Hydrolyzed Rice Protein", "Body"],
        ["Panthenol", "Moisture"],
      ],
    },
    {
      id: "leave-in-mist",
      step: "Step 04 — Protect",
      name: "Thermal Shield Leave-In Mist",
      size: "150 ml",
      price: 32,
      label: "Protect",
      image: "./assets/leave-in-mist.png",
      desc: "Leichter Leave-In Schutz für Styling, Hitze und Frizz-Kontrolle. Mit Hydrolyzed Vegetable Protein PG-Propyl Silanetriol, Panthenol, Polyquaternium-55 und Keratin Amino Acids.",
      actives: [
        ["Hydrolyzed Vegetable Protein PG-Propyl Silanetriol", "Shield"],
        ["Panthenol", "Moisture"],
        ["Polyquaternium-55", "Control"],
        ["Keratin Amino Acids", "Strength"],
      ],
    },
    {
      id: "scalp-serum",
      step: "Step 05 — Signal",
      name: "BICOL+ Biomimetic Scalp Signal Serum",
      size: "60 ml",
      price: 54,
      label: "Scalp Care",
      image: "./assets/scalp-serum.png",
      desc: "Ein biomimetisches Scalp Serum für die tägliche Kopfhautpflege. Mit Octapeptide-2, Biotinoyl Tripeptide-1, Copper Tripeptide-1 und Niacinamide.",
      actives: [
        ["Octapeptide-2", "Signal"],
        ["Biotinoyl Tripeptide-1", "Signal"],
        ["Copper Tripeptide-1", "Signal"],
        ["Niacinamide", "Scalp"],
      ],
    },
  ];

  const BUNDLES = [
    {
      id: "essential-ritual",
      name: "Essential Ritual",
      tagline: "Der Einstieg in die STRÆHN Routine.",
      items: ["shampoo", "conditioner", "treatment"],
      price: 98,
      featured: false,
      cta: "Essential entdecken",
      image: "./assets/shampoo.png",
    },
    {
      id: "complete-ritual",
      name: "Complete Ritual",
      tagline: "Die vollständige Routine für Pflege, Glanz und Schutz.",
      items: ["shampoo", "conditioner", "treatment", "leave-in-mist"],
      price: 126,
      featured: true,
      cta: "Complete entdecken",
      image: "./assets/treatment.png",
    },
    {
      id: "signature-ritual",
      name: "Signature Ritual",
      tagline: "Das volle STRÆHN Ritual für Haar und Kopfhaut.",
      items: ["shampoo", "conditioner", "treatment", "leave-in-mist", "scalp-serum"],
      price: 168,
      featured: false,
      cta: "Signature entdecken",
      image: "./assets/scalp-serum.png",
    },
  ];

  const byId = (id) =>
    PRODUCTS.find((p) => p.id === id) || BUNDLES.find((b) => b.id === id);

  const stepLabel = (productId) => {
    const p = PRODUCTS.find((x) => x.id === productId);
    return p ? p.step.split("—")[1].trim() : "";
  };

  const money = (n) => "€" + n;

  /* ---------- Render: product grid ---------- */

  const grid = document.getElementById("productGrid");

  grid.innerHTML = PRODUCTS.map(
    (p) => `
    <article class="product-card reveal" data-id="${p.id}">
      <div class="product-card__media" data-quickview="${p.id}" title="${p.name} ansehen">
        <img src="${p.image}" alt="STRÆHN ${p.name}" loading="lazy" />
        <span class="product-card__label">${p.label}</span>
      </div>
      <div class="product-card__body">
        <p class="product-card__step">${p.step}</p>
        <h3 class="product-card__name">${p.name}</h3>
        <p class="product-card__size">${p.size}</p>
        <p class="product-card__desc">${p.desc}</p>
        <div class="product-card__row">
          <span class="product-card__price">${money(p.price)}</span>
        </div>
        <div class="product-card__actions">
          <button class="btn btn--ghost btn--sm" data-quickview="${p.id}" type="button">Zum Produkt</button>
          <button class="btn btn--dark btn--sm" data-add="${p.id}" type="button">In den Warenkorb</button>
        </div>
      </div>
    </article>`
  ).join("");

  /* ---------- Render: bundles ---------- */

  const bundleGrid = document.getElementById("bundleGrid");

  bundleGrid.innerHTML = BUNDLES.map((b) => {
    const compare = b.items.reduce((sum, id) => sum + byId(id).price, 0);
    return `
    <article class="bundle-card reveal ${b.featured ? "bundle-card--featured" : ""}" data-id="${b.id}">
      ${b.featured ? '<span class="bundle-card__badge">Recommended</span>' : ""}
      <h3 class="bundle-card__name">${b.name}</h3>
      <p class="bundle-card__tagline">${b.tagline}</p>
      <ul class="bundle-card__items">
        ${b.items
          .map(
            (id) =>
              `<li><span>${byId(id).name}</span><span>${stepLabel(id)}</span></li>`
          )
          .join("")}
      </ul>
      <div class="bundle-card__pricing">
        <span class="bundle-card__price">${money(b.price)}</span>
        <span class="bundle-card__compare">${money(compare)}</span>
        <span class="bundle-card__hint">Vollständige Routine</span>
      </div>
      <button class="btn btn--dark btn--full" data-add="${b.id}" type="button">${b.cta}</button>
    </article>`;
  }).join("");

  /* ---------- Cart state ---------- */

  const STORAGE_KEY = "straehn-cart";

  let cart = [];
  try {
    cart = JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
  } catch (e) {
    cart = [];
  }

  const cartDrawer = document.getElementById("cartDrawer");
  const cartBody = document.getElementById("cartBody");
  const cartFoot = document.getElementById("cartFoot");
  const cartTotal = document.getElementById("cartTotal");
  const cartCount = document.getElementById("cartCount");
  const drawerBackdrop = document.getElementById("drawerBackdrop");

  function saveCart() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(cart));
    } catch (e) {
      /* private mode — cart lives in memory only */
    }
  }

  function cartQty() {
    return cart.reduce((n, item) => n + item.qty, 0);
  }

  function renderCart() {
    const qty = cartQty();
    cartCount.hidden = qty === 0;
    cartCount.textContent = qty;

    if (cart.length === 0) {
      cartBody.innerHTML = `
        <div class="cart__empty">
          <p>Dein Warenkorb ist leer.</p>
          <p>Beginne dein Ritual mit einem der fünf Schritte.</p>
        </div>`;
      cartFoot.style.display = "none";
      return;
    }

    cartFoot.style.display = "";

    cartBody.innerHTML = cart
      .map((item) => {
        const p = byId(item.id);
        const meta = p.size || "Ritual Set";
        return `
        <div class="cart-item" data-id="${item.id}">
          <img class="cart-item__img" src="${p.image}" alt="${p.name}" />
          <div>
            <p class="cart-item__name">${p.name}</p>
            <p class="cart-item__meta">${meta}</p>
            <div class="qty">
              <button data-dec="${item.id}" aria-label="Menge verringern" type="button">−</button>
              <span>${item.qty}</span>
              <button data-inc="${item.id}" aria-label="Menge erhöhen" type="button">+</button>
            </div>
          </div>
          <div class="cart-item__right">
            <span class="cart-item__price">${money(p.price * item.qty)}</span>
            <button class="cart-item__remove" data-remove="${item.id}" type="button">Entfernen</button>
          </div>
        </div>`;
      })
      .join("");

    const total = cart.reduce((sum, item) => sum + byId(item.id).price * item.qty, 0);
    cartTotal.textContent = money(total);
  }

  function addToCart(id, openDrawer = true) {
    const existing = cart.find((item) => item.id === id);
    if (existing) existing.qty += 1;
    else cart.push({ id, qty: 1 });
    saveCart();
    renderCart();
    if (openDrawer) setCartOpen(true);
    else showToast("Zum Ritual hinzugefügt");
  }

  function changeQty(id, delta) {
    const item = cart.find((x) => x.id === id);
    if (!item) return;
    item.qty += delta;
    if (item.qty <= 0) cart = cart.filter((x) => x.id !== id);
    saveCart();
    renderCart();
  }

  function removeFromCart(id) {
    cart = cart.filter((x) => x.id !== id);
    saveCart();
    renderCart();
  }

  function setCartOpen(open) {
    cartDrawer.classList.toggle("is-open", open);
    cartDrawer.setAttribute("aria-hidden", String(!open));
    drawerBackdrop.hidden = !open;
    requestAnimationFrame(() => drawerBackdrop.classList.toggle("is-visible", open));
    document.body.style.overflow = open || modal.classList.contains("is-open") ? "hidden" : "";
  }

  document.getElementById("cartToggle").addEventListener("click", () => setCartOpen(true));
  document.getElementById("cartClose").addEventListener("click", () => setCartOpen(false));
  drawerBackdrop.addEventListener("click", () => setCartOpen(false));

  document.getElementById("checkoutBtn").addEventListener("click", () => {
    showToast("Checkout folgt zum Launch");
  });

  /* ---------- Product quick view ---------- */

  const modal = document.getElementById("productModal");
  const modalContent = document.getElementById("modalContent");
  const modalBackdrop = document.getElementById("modalBackdrop");

  function openModal(id) {
    const p = PRODUCTS.find((x) => x.id === id);
    if (!p) return;

    modalContent.innerHTML = `
      <div class="modal__media">
        <img src="${p.image}" alt="STRÆHN ${p.name}" />
      </div>
      <div class="modal__body">
        <p class="modal__step">${p.step}</p>
        <h2 class="modal__name">${p.name}</h2>
        <p class="modal__size">${p.size}</p>
        <p class="modal__desc">${p.desc}</p>
        <ul class="modal__actives">
          ${p.actives.map(([name, role]) => `<li><span>${name}</span><span>${role}</span></li>`).join("")}
        </ul>
        <div class="modal__buy">
          <span class="modal__price">${money(p.price)}</span>
          <button class="btn btn--dark" data-add="${p.id}" data-close-modal type="button">In den Warenkorb</button>
        </div>
      </div>`;

    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    modalBackdrop.hidden = false;
    requestAnimationFrame(() => modalBackdrop.classList.add("is-visible"));
    document.body.style.overflow = "hidden";
  }

  function closeModal() {
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    modalBackdrop.classList.remove("is-visible");
    setTimeout(() => {
      modalBackdrop.hidden = true;
    }, 400);
    if (!cartDrawer.classList.contains("is-open")) document.body.style.overflow = "";
  }

  document.getElementById("modalClose").addEventListener("click", closeModal);
  modalBackdrop.addEventListener("click", closeModal);

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeModal();
      setCartOpen(false);
    }
  });

  /* ---------- Delegated clicks (add / quickview / qty) ---------- */

  document.addEventListener("click", (e) => {
    const add = e.target.closest("[data-add]");
    if (add) {
      if (add.hasAttribute("data-close-modal")) closeModal();
      addToCart(add.getAttribute("data-add"));
      return;
    }

    const quick = e.target.closest("[data-quickview]");
    if (quick) {
      openModal(quick.getAttribute("data-quickview"));
      return;
    }

    const inc = e.target.closest("[data-inc]");
    if (inc) return changeQty(inc.getAttribute("data-inc"), 1);

    const dec = e.target.closest("[data-dec]");
    if (dec) return changeQty(dec.getAttribute("data-dec"), -1);

    const remove = e.target.closest("[data-remove]");
    if (remove) return removeFromCart(remove.getAttribute("data-remove"));
  });

  /* ---------- Toast ---------- */

  const toast = document.getElementById("toast");
  let toastTimer;

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add("is-visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("is-visible"), 2400);
  }

  /* ---------- Header / mobile nav ---------- */

  const header = document.getElementById("header");
  const mobileNav = document.getElementById("mobileNav");
  const navToggle = document.getElementById("navToggle");

  window.addEventListener(
    "scroll",
    () => {
      header.classList.toggle("is-scrolled", window.scrollY > 8);
    },
    { passive: true }
  );

  navToggle.addEventListener("click", () => {
    const open = !mobileNav.classList.contains("is-open");
    mobileNav.classList.toggle("is-open", open);
    mobileNav.setAttribute("aria-hidden", String(!open));
    navToggle.setAttribute("aria-label", open ? "Menü schließen" : "Menü öffnen");
    document.body.style.overflow = open ? "hidden" : "";
  });

  mobileNav.querySelectorAll("a").forEach((link) =>
    link.addEventListener("click", () => {
      mobileNav.classList.remove("is-open");
      mobileNav.setAttribute("aria-hidden", "true");
      document.body.style.overflow = "";
    })
  );

  /* ---------- Sticky mobile CTA ---------- */

  const stickyCta = document.getElementById("stickyCta");
  const hero = document.querySelector(".hero");
  const ritual = document.getElementById("ritual");

  function updateStickyCta() {
    if (window.innerWidth > 760) {
      stickyCta.classList.remove("is-visible");
      document.body.classList.remove("has-sticky-cta");
      return;
    }
    const pastHero = window.scrollY > hero.offsetTop + hero.offsetHeight * 0.6;
    const beforeRitual = window.scrollY < ritual.offsetTop - window.innerHeight * 0.5;
    const visible = pastHero && beforeRitual;
    stickyCta.classList.toggle("is-visible", visible);
    document.body.classList.toggle("has-sticky-cta", visible);
  }

  window.addEventListener("scroll", updateStickyCta, { passive: true });
  window.addEventListener("resize", updateStickyCta);
  updateStickyCta();

  /* ---------- Newsletter ---------- */

  const form = document.getElementById("newsletterForm");
  const emailInput = document.getElementById("newsletterEmail");
  const success = document.getElementById("newsletterSuccess");

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const value = emailInput.value.trim();
    if (!value || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
      emailInput.focus();
      showToast("Bitte gültige E-Mail eingeben");
      return;
    }
    form.hidden = true;
    success.hidden = false;
  });

  /* ---------- Reveal on scroll ---------- */

  if (!("IntersectionObserver" in window)) {
    document.querySelectorAll(".reveal").forEach((el) => el.classList.add("is-inview"));
    renderCart();
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-inview");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
  );

  document.querySelectorAll(".reveal").forEach((el) => observer.observe(el));

  /* ---------- Init ---------- */

  renderCart();
})();
