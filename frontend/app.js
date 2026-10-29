/**
 * Клиентский модуль взаимодействия с REST API интернет-магазина (/api/v1/*).
 * Использует исключительно семантические HTML5-элементы (article, header, footer, section, tr, td, output).
 */

const API_BASE = "/api/v1";

const state = {
  token: localStorage.getItem("ecommerce_jwt") || null,
  user: null,
  categories: [],
  currentPage: 1,
  totalPages: 1,
  activeView: "catalog",
};

/**
 * Универсальная обертка над Fetch API с автоматической подстановкой JWT и разбором ошибок.
 */
async function apiRequest(endpoint, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  if (state.token) {
    headers["Authorization"] = `Bearer ${state.token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload.status === "error") {
    const message = payload?.error?.message || `Ошибка HTTP ${response.status}`;
    throw new Error(message);
  }
  return payload;
}

/**
 * Вывод краткого уведомления о результате операции.
 */
function notify(message, type = "info") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("output");
  toast.dataset.type = type;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3800);
}

function formatPrice(value) {
  return `${Number(value).toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ₽`;
}

/**
 * Проверка доступности бэкенда (/api/v1/health).
 */
async function checkBackendHealth() {
  const indicator = document.getElementById("api-status-indicator");
  try {
    const res = await apiRequest("/health");
    indicator.textContent = `API: ${res.data.status} (200 OK)`;
  } catch (err) {
    indicator.textContent = "API: недоступен";
  }
}

/**
 * Восстановление сессии по сохраненному JWT-токену (/api/v1/auth/me).
 */
async function restoreSession() {
  if (!state.token) {
    updateSessionUI();
    return;
  }
  try {
    const res = await apiRequest("/auth/me");
    state.user = res.data;
  } catch (err) {
    state.token = null;
    state.user = null;
    localStorage.removeItem("ecommerce_jwt");
  }
  updateSessionUI();
}

/**
 * Синхронизация шапки профиля и доступности вкладок по роли пользователя.
 */
function updateSessionUI() {
  const userDisplay = document.getElementById("user-display");
  const btnOpenAuth = document.getElementById("btn-open-auth");
  const btnLogout = document.getElementById("btn-logout");
  const navStaffItem = document.getElementById("nav-staff-item");
  const adminUsersSection = document.getElementById("admin-users-section");

  if (state.user) {
    userDisplay.textContent = `${state.user.full_name} (${state.user.role})`;
    btnOpenAuth.hidden = true;
    btnLogout.hidden = false;

    const isStaff = state.user.role === "manager" || state.user.role === "admin";
    navStaffItem.hidden = !isStaff;
    adminUsersSection.hidden = state.user.role !== "admin";
    refreshCartBadge();
  } else {
    userDisplay.textContent = "Гость";
    btnOpenAuth.hidden = false;
    btnLogout.hidden = true;
    navStaffItem.hidden = true;
    adminUsersSection.hidden = true;
    document.getElementById("cart-badge").textContent = "0";
  }
}

/**
 * Переключение между основными представлениями (Каталог / Корзина / Заказы / Управление).
 */
function switchView(viewName) {
  const views = ["catalog", "cart", "orders", "staff"];
  views.forEach((v) => {
    const section = document.getElementById(`view-${v}`);
    if (section) section.hidden = v !== viewName;
  });

  document.querySelectorAll("header nav a[data-nav]").forEach((link) => {
    if (link.dataset.nav === viewName) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  });

  state.activeView = viewName;

  if (viewName === "catalog") loadProducts();
  if (viewName === "cart") loadCart();
  if (viewName === "orders") loadOrders();
  if (viewName === "staff") loadStaffDashboard();
}

/**
 * Загрузка списка категорий (/api/v1/categories) и заполнение выпадающих списков.
 */
async function loadCategories() {
  try {
    const res = await apiRequest("/categories");
    state.categories = res.data || [];

    const filterSelect = document.getElementById("filter-category");
    const staffSelect = document.getElementById("staff-product-category");

    filterSelect.innerHTML = '<option value="">Все категории</option>';
    staffSelect.innerHTML = "";

    state.categories.forEach((cat) => {
      const opt1 = document.createElement("option");
      opt1.value = String(cat.id);
      opt1.textContent = cat.name;
      filterSelect.appendChild(opt1);

      const opt2 = document.createElement("option");
      opt2.value = String(cat.id);
      opt2.textContent = `${cat.name} (${cat.slug})`;
      staffSelect.appendChild(opt2);
    });
  } catch (err) {
    notify(`Ошибка загрузки категорий: ${err.message}`, "error");
  }
}

/**
 * Загрузка и отрисовка каталога товаров (/api/v1/products) с учетом фильтров и пагинации.
 */
async function loadProducts() {
  const params = new URLSearchParams();
  params.set("page", String(state.currentPage));
  params.set("per_page", "12");

  const searchVal = document.getElementById("search-input").value.trim();
  const categoryVal = document.getElementById("filter-category").value;
  const minPriceVal = document.getElementById("filter-min-price").value;
  const maxPriceVal = document.getElementById("filter-max-price").value;
  const inStockChecked = document.getElementById("filter-in-stock").checked;

  if (searchVal) params.set("q", searchVal);
  if (categoryVal) params.set("category_id", categoryVal);
  if (minPriceVal) params.set("min_price", minPriceVal);
  if (maxPriceVal) params.set("max_price", maxPriceVal);
  if (inStockChecked) params.set("in_stock", "true");

  try {
    const res = await apiRequest(`/products?${params.toString()}`);
    const products = res.data || [];
    const meta = res.meta || { page: 1, total_pages: 1, total_items: products.length };

    state.totalPages = Math.max(1, meta.total_pages);
    document.getElementById("catalog-meta").textContent = `Найдено позиций: ${meta.total_items}`;

    const grid = document.getElementById("product-grid");
    grid.innerHTML = "";

    products.forEach((prod) => {
      const li = document.createElement("li");
      const article = document.createElement("article");

      const hdr = document.createElement("header");
      const skuTag = document.createElement("small");
      skuTag.textContent = `${prod.sku} · ${prod.category_name || "Каталог"}`;
      const title = document.createElement("h2");
      title.textContent = prod.name;
      hdr.append(skuTag, title);

      const desc = document.createElement("p");
      desc.textContent = prod.description || "Описание не указано.";

      const ftr = document.createElement("footer");
      const priceElem = document.createElement("data");
      priceElem.value = String(prod.price);
      priceElem.textContent = formatPrice(prod.price);

      const stockBadge = document.createElement("span");
      if (prod.stock > 0) {
        stockBadge.dataset.stock = "ok";
        stockBadge.textContent = `В наличии: ${prod.stock} шт.`;
      } else {
        stockBadge.dataset.stock = "empty";
        stockBadge.textContent = "Нет в наличии";
      }

      const addBtn = document.createElement("button");
      addBtn.type = "button";
      addBtn.dataset.variant = "primary";
      addBtn.textContent = "В корзину";
      addBtn.disabled = prod.stock <= 0;
      addBtn.addEventListener("click", () => addProductToCart(prod.id));

      ftr.append(priceElem, stockBadge, addBtn);
      article.append(hdr, desc, ftr);
      li.appendChild(article);
      grid.appendChild(li);
    });

    const pagBar = document.getElementById("pagination-bar");
    pagBar.hidden = state.totalPages <= 1;
    document.getElementById("pagination-info").textContent = `Страница ${meta.page} из ${state.totalPages}`;
    document.getElementById("btn-prev-page").disabled = meta.page <= 1;
    document.getElementById("btn-next-page").disabled = meta.page >= state.totalPages;
  } catch (err) {
    notify(`Ошибка загрузки каталога: ${err.message}`, "error");
  }
}

/**
 * Обновление счетчика товаров в шапке.
 */
async function refreshCartBadge() {
  if (!state.user) return;
  try {
    const res = await apiRequest("/cart");
    document.getElementById("cart-badge").textContent = String(res.data.total_quantity || 0);
  } catch (_) {
    // Игнорируем фоновую ошибку
  }
}

/**
 * Добавление 1 шт. товара в корзину с проверкой текущего количества.
 */
async function addProductToCart(productId) {
  if (!state.user) {
    document.getElementById("auth-dialog").showModal();
    notify("Войдите в аккаунт для добавления товаров в корзину");
    return;
  }
  try {
    const currentCart = await apiRequest("/cart");
    const existing = (currentCart.data.items || []).find((i) => i.product_id === productId);
    const nextQty = existing ? existing.quantity + 1 : 1;

    const updated = await apiRequest("/cart/items", {
      method: "POST",
      body: JSON.stringify({ product_id: productId, quantity: nextQty }),
    });
    document.getElementById("cart-badge").textContent = String(updated.data.total_quantity || 0);
    notify("Товар добавлен в корзину");
  } catch (err) {
    notify(err.message, "error");
  }
}

/**
 * Загрузка и отображение корзины покупателя (/api/v1/cart).
 */
async function loadCart() {
  if (!state.user) {
    notify("Авторизуйтесь для просмотра корзины");
    document.getElementById("auth-dialog").showModal();
    return;
  }
  try {
    const res = await apiRequest("/cart");
    renderCartData(res.data);
  } catch (err) {
    notify(err.message, "error");
  }
}

function renderCartData(cartData) {
  const tbody = document.getElementById("cart-tbody");
  tbody.innerHTML = "";

  const items = cartData.items || [];
  document.getElementById("cart-badge").textContent = String(cartData.total_quantity || 0);
  document.getElementById("cart-summary-qty").textContent = `${cartData.total_quantity || 0} шт.`;
  document.getElementById("cart-summary-total").textContent = formatPrice(cartData.total_amount || 0);

  if (items.length === 0) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 7;
    td.textContent = "Корзина пуста. Перейдите в каталог, чтобы выбрать товары.";
    tr.appendChild(td);
    tbody.appendChild(tr);
    return;
  }

  items.forEach((item) => {
    const tr = document.createElement("tr");

    const tdSku = document.createElement("td");
    tdSku.textContent = item.sku || `#${item.product_id}`;

    const tdName = document.createElement("td");
    tdName.textContent = item.product_name;

    const tdPrice = document.createElement("td");
    tdPrice.textContent = formatPrice(item.unit_price);

    const tdQty = document.createElement("td");
    const qtyInput = document.createElement("input");
    qtyInput.type = "number";
    qtyInput.min = "0";
    qtyInput.max = String(item.available_stock);
    qtyInput.value = String(item.quantity);
    qtyInput.addEventListener("change", async () => {
      try {
        const updated = await apiRequest("/cart/items", {
          method: "POST",
          body: JSON.stringify({ product_id: item.product_id, quantity: Number(qtyInput.value) }),
        });
        renderCartData(updated.data);
      } catch (err) {
        notify(err.message, "error");
        loadCart();
      }
    });
    tdQty.appendChild(qtyInput);

    const tdStock = document.createElement("td");
    tdStock.textContent = `${item.available_stock} шт.`;

    const tdSubtotal = document.createElement("td");
    const strongSub = document.createElement("strong");
    strongSub.textContent = formatPrice(item.subtotal);
    tdSubtotal.appendChild(strongSub);

    const tdAct = document.createElement("td");
    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.dataset.variant = "danger";
    delBtn.textContent = "Удалить";
    delBtn.addEventListener("click", async () => {
      try {
        const updated = await apiRequest(`/cart/items/${item.product_id}`, { method: "DELETE" });
        renderCartData(updated.data);
      } catch (err) {
        notify(err.message, "error");
      }
    });
    tdAct.appendChild(delBtn);

    tr.append(tdSku, tdName, tdPrice, tdQty, tdStock, tdSubtotal, tdAct);
    tbody.appendChild(tr);
  });
}

/**
 * Загрузка списка заказов (/api/v1/orders) и детальных позиций каждого заказа.
 */
async function loadOrders() {
  if (!state.user) {
    notify("Авторизуйтесь для просмотра заказов");
    document.getElementById("auth-dialog").showModal();
    return;
  }

  const statusFilter = document.getElementById("orders-status-filter").value;
  const query = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : "";

  try {
    const res = await apiRequest(`/orders${query}`);
    const orders = res.data || [];
    const listEl = document.getElementById("orders-list");
    listEl.innerHTML = "";

    if (orders.length === 0) {
      const li = document.createElement("li");
      const article = document.createElement("article");
      const p = document.createElement("p");
      p.textContent = "Заказы не найдены.";
      article.appendChild(p);
      li.appendChild(article);
      listEl.appendChild(li);
      return;
    }

    for (const ordSummary of orders) {
      const detailRes = await apiRequest(`/orders/${ordSummary.id}`);
      const ord = detailRes.data;

      const li = document.createElement("li");
      const article = document.createElement("article");

      const hdr = document.createElement("header");
      const h2 = document.createElement("h2");
      h2.textContent = `Заказ #${ord.id} от ${new Date(ord.created_at).toLocaleString("ru-RU")}`;
      const statusMark = document.createElement("mark");
      statusMark.dataset.status = ord.status;
      statusMark.textContent = ord.status;
      hdr.append(h2, statusMark);

      const metaP = document.createElement("p");
      metaP.textContent = `Покупатель: ${ord.user_email || ord.user_id} | Адрес доставки: ${ord.shipping_address}${ord.comment ? ` (${ord.comment})` : ""}`;

      const itemsTable = document.createElement("table");
      const thead = document.createElement("thead");
      thead.innerHTML = "<tr><th>SKU</th><th>Товар (снимок на момент покупки)</th><th>Цена фиксации</th><th>Кол-во</th><th>Сумма</th></tr>";
      const tbody = document.createElement("tbody");

      (ord.items || []).forEach((it) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${it.sku}</td><td>${it.product_name}</td><td>${formatPrice(it.unit_price)}</td><td>${it.quantity} шт.</td><td><strong>${formatPrice(it.subtotal)}</strong></td>`;
        tbody.appendChild(tr);
      });
      itemsTable.append(thead, tbody);

      const ftr = document.createElement("footer");
      const totalStrong = document.createElement("strong");
      totalStrong.textContent = `Итого по заказу: ${formatPrice(ord.total_amount)}`;
      ftr.appendChild(totalStrong);

      // Кнопка отмены для покупателя (если заказ еще в статусе pending)
      if (state.user.role === "customer" && ord.status === "pending") {
        const cancelBtn = document.createElement("button");
        cancelBtn.type = "button";
        cancelBtn.dataset.variant = "danger";
        cancelBtn.textContent = "Отменить заказ (вернуть на склад)";
        cancelBtn.addEventListener("click", async () => {
          try {
            await apiRequest(`/orders/${ord.id}/cancel`, { method: "POST" });
            notify(`Заказ #${ord.id} отменен, товары возвращены на склад`);
            loadOrders();
          } catch (err) {
            notify(err.message, "error");
          }
        });
        ftr.appendChild(cancelBtn);
      }

      // Управление статусом заказа для Менеджера и Администратора
      if (state.user.role === "manager" || state.user.role === "admin") {
        const statusForm = document.createElement("form");
        statusForm.style.display = "flex";
        statusForm.style.gap = "8px";
        const sel = document.createElement("select");
        ["pending", "paid", "shipped", "completed", "cancelled"].forEach((st) => {
          const opt = document.createElement("option");
          opt.value = st;
          opt.textContent = st;
          opt.selected = st === ord.status;
          sel.appendChild(opt);
        });
        const applyBtn = document.createElement("button");
        applyBtn.type = "submit";
        applyBtn.dataset.variant = "primary";
        applyBtn.textContent = "Сменить статус";

        statusForm.append(sel, applyBtn);
        statusForm.addEventListener("submit", async (e) => {
          e.preventDefault();
          try {
            await apiRequest(`/orders/${ord.id}/status`, {
              method: "PATCH",
              body: JSON.stringify({ status: sel.value }),
            });
            notify(`Статус заказа #${ord.id} изменен на '${sel.value}'`);
            loadOrders();
          } catch (err) {
            notify(err.message, "error");
          }
        });
        ftr.appendChild(statusForm);
      }

      article.append(hdr, metaP, itemsTable, ftr);
      li.appendChild(article);
      listEl.appendChild(li);
    }
  } catch (err) {
    notify(err.message, "error");
  }
}

/**
 * Загрузка панели управления и аналитики (/api/v1/admin/stats и /api/v1/admin/users).
 */
async function loadStaffDashboard() {
  if (!state.user || (state.user.role !== "manager" && state.user.role !== "admin")) {
    notify("Недостаточно прав для доступа к панели управления", "error");
    return;
  }

  try {
    const statsRes = await apiRequest("/admin/stats");
    const st = statsRes.data;
    document.getElementById("stat-users").textContent = String(st.users_count);
    document.getElementById("stat-products").textContent = String(st.products_count);
    document.getElementById("stat-out-of-stock").textContent = String(st.out_of_stock_active_products);
    document.getElementById("stat-orders").textContent = String(st.orders_total);
    document.getElementById("stat-revenue").textContent = formatPrice(st.confirmed_revenue);
  } catch (err) {
    notify(err.message, "error");
  }

  if (state.user.role === "admin") {
    try {
      const usersRes = await apiRequest("/admin/users");
      const tbody = document.getElementById("admin-users-tbody");
      tbody.innerHTML = "";

      (usersRes.data || []).forEach((u) => {
        const tr = document.createElement("tr");

        const tdId = document.createElement("td");
        tdId.textContent = `#${u.id}`;

        const tdEmail = document.createElement("td");
        tdEmail.textContent = u.email;

        const tdName = document.createElement("td");
        tdName.textContent = u.full_name;

        const tdRole = document.createElement("td");
        const roleSelect = document.createElement("select");
        ["customer", "manager", "admin"].forEach((r) => {
          const opt = document.createElement("option");
          opt.value = r;
          opt.textContent = r;
          opt.selected = r === u.role;
          roleSelect.appendChild(opt);
        });
        tdRole.appendChild(roleSelect);

        const tdActive = document.createElement("td");
        const activeCheckbox = document.createElement("input");
        activeCheckbox.type = "checkbox";
        activeCheckbox.checked = u.is_active;
        tdActive.appendChild(activeCheckbox);

        const tdAction = document.createElement("td");
        const saveBtn = document.createElement("button");
        saveBtn.type = "button";
        saveBtn.dataset.variant = "primary";
        saveBtn.textContent = "Сохранить";
        saveBtn.addEventListener("click", async () => {
          try {
            await apiRequest(`/admin/users/${u.id}`, {
              method: "PATCH",
              body: JSON.stringify({
                role: roleSelect.value,
                is_active: activeCheckbox.checked,
              }),
            });
            notify(`Права пользователя ${u.email} обновлены`);
            loadStaffDashboard();
          } catch (err) {
            notify(err.message, "error");
            loadStaffDashboard();
          }
        });
        tdAction.appendChild(saveBtn);

        tr.append(tdId, tdEmail, tdName, tdRole, tdActive, tdAction);
        tbody.appendChild(tr);
      });
    } catch (err) {
      notify(err.message, "error");
    }
  }
}

/**
 * Привязка всех обработчиков событий после загрузки DOM.
 */
document.addEventListener("DOMContentLoaded", async () => {
  await checkBackendHealth();
  await loadCategories();
  await restoreSession();
  await loadProducts();

  // Навигация по вкладкам
  document.querySelectorAll("[data-nav]").forEach((el) => {
    el.addEventListener("click", (e) => {
      e.preventDefault();
      switchView(el.dataset.nav);
    });
  });

  // Быстрый вход одним кликом по тестовым ролям из seed.py
  document.querySelectorAll("[data-quick-email]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        const res = await apiRequest("/auth/login", {
          method: "POST",
          body: JSON.stringify({
            email: btn.dataset.quickEmail,
            password: btn.dataset.quickPass,
          }),
        });
        state.token = res.data.access_token;
        state.user = res.data.user;
        localStorage.setItem("ecommerce_jwt", state.token);
        updateSessionUI();
        notify(`Выполнен вход: ${state.user.full_name} (${state.user.role})`);
        switchView(state.activeView);
      } catch (err) {
        notify(`Ошибка быстрого входа (убедитесь, что выполнен python seed.py): ${err.message}`, "error");
      }
    });
  });

  // Открытие и закрытие модального окна авторизации
  const authDialog = document.getElementById("auth-dialog");
  document.getElementById("btn-open-auth").addEventListener("click", () => authDialog.showModal());
  document.getElementById("btn-close-auth").addEventListener("click", () => authDialog.close());

  // Выход из аккаунта
  document.getElementById("btn-logout").addEventListener("click", () => {
    state.token = null;
    state.user = null;
    localStorage.removeItem("ecommerce_jwt");
    updateSessionUI();
    switchView("catalog");
    notify("Вы вышли из системы");
  });

  // Вход через форму
  document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      const res = await apiRequest("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: fd.get("email"),
          password: fd.get("password"),
        }),
      });
      state.token = res.data.access_token;
      state.user = res.data.user;
      localStorage.setItem("ecommerce_jwt", state.token);
      e.target.reset();
      authDialog.close();
      updateSessionUI();
      notify("Вход выполнен успешно");
    } catch (err) {
      notify(err.message, "error");
    }
  });

  // Регистрация через форму
  document.getElementById("register-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      const res = await apiRequest("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          full_name: fd.get("full_name"),
          email: fd.get("email"),
          password: fd.get("password"),
        }),
      });
      state.token = res.data.access_token;
      state.user = res.data.user;
      localStorage.setItem("ecommerce_jwt", state.token);
      e.target.reset();
      authDialog.close();
      updateSessionUI();
      notify("Регистрация успешно завершена");
    } catch (err) {
      notify(err.message, "error");
    }
  });

  // Поиск и фильтрация каталога
  document.getElementById("search-form").addEventListener("submit", (e) => {
    e.preventDefault();
    state.currentPage = 1;
    switchView("catalog");
  });

  document.getElementById("filter-form").addEventListener("submit", (e) => {
    e.preventDefault();
    state.currentPage = 1;
    loadProducts();
  });

  document.getElementById("btn-reset-filters").addEventListener("click", () => {
    setTimeout(() => {
      document.getElementById("search-input").value = "";
      state.currentPage = 1;
      loadProducts();
    }, 10);
  });

  // Пагинация
  document.getElementById("btn-prev-page").addEventListener("click", () => {
    if (state.currentPage > 1) {
      state.currentPage -= 1;
      loadProducts();
    }
  });

  document.getElementById("btn-next-page").addEventListener("click", () => {
    if (state.currentPage < state.totalPages) {
      state.currentPage += 1;
      loadProducts();
    }
  });

  // Очистка корзины
  document.getElementById("btn-clear-cart").addEventListener("click", async () => {
    try {
      const res = await apiRequest("/cart", { method: "DELETE" });
      renderCartData(res.data);
      notify("Корзина очищена");
    } catch (err) {
      notify(err.message, "error");
    }
  });

  // Оформление заказа (Checkout)
  document.getElementById("checkout-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const address = document.getElementById("checkout-address").value.trim();
    const comment = document.getElementById("checkout-comment").value.trim();
    try {
      const res = await apiRequest("/orders/checkout", {
        method: "POST",
        body: JSON.stringify({
          shipping_address: address,
          comment: comment || null,
        }),
      });
      e.target.reset();
      await refreshCartBadge();
      notify(`Заказ #${res.data.id} успешно оформлен`);
      switchView("orders");
    } catch (err) {
      notify(err.message, "error");
    }
  });

  // Фильтр заказов по статусу
  document.getElementById("orders-status-filter").addEventListener("change", () => loadOrders());

  // Создание категории персоналом
  document.getElementById("form-create-category").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await apiRequest("/categories", {
        method: "POST",
        body: JSON.stringify({
          name: fd.get("name"),
          slug: fd.get("slug"),
          description: fd.get("description") || null,
        }),
      });
      e.target.reset();
      await loadCategories();
      notify("Категория создана");
    } catch (err) {
      notify(err.message, "error");
    }
  });

  // Создание товара персоналом
  document.getElementById("form-create-product").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await apiRequest("/products", {
        method: "POST",
        body: JSON.stringify({
          category_id: Number(fd.get("category_id")),
          sku: fd.get("sku"),
          name: fd.get("name"),
          price: fd.get("price"),
          stock: Number(fd.get("stock")),
          description: fd.get("description") || null,
        }),
      });
      e.target.reset();
      await loadStaffDashboard();
      notify("Товар добавлен в каталог");
    } catch (err) {
      notify(err.message, "error");
    }
  });
});
