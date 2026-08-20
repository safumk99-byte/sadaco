from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import product_manager_required
from .forms import ProductCategoryForm, ProductForm, StockTransactionForm
from .models import Product, ProductCategory, StockTransaction
from .services import can_manage_products, dashboard_stats, product_queryset, search_products


@login_required
def product_list(request):
    query = request.GET.get("q", "").strip()
    products = search_products(query)
    return render(request, "products/product_list.html", {
        "title": "Product Management",
        "products": products,
        "query": query,
        "stats": dashboard_stats(),
        "can_manage": can_manage_products(request.user),
    })


@product_manager_required
def category_list(request):
    return render(request, "products/categories.html", {
        "title": "Product Categories",
        "categories": ProductCategory.objects.all(),
    })


@product_manager_required
def category_create(request):
    form = ProductCategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Product category created successfully.")
        return redirect("products:categories")
    return render(request, "products/form.html", {
        "title": "Add Product Category", "form": form, "back_url": "products:categories"
    })


@product_manager_required
def category_edit(request, pk):
    category = get_object_or_404(ProductCategory, pk=pk)
    form = ProductCategoryForm(request.POST or None, instance=category)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Product category updated successfully.")
        return redirect("products:categories")
    return render(request, "products/form.html", {
        "title": "Edit Product Category", "form": form, "back_url": "products:categories"
    })


@product_manager_required
def product_create(request):
    form = ProductForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Product created successfully.")
        return redirect("products:list")
    return render(request, "products/form.html", {
        "title": "Add Product", "form": form, "back_url": "products:list"
    })


@product_manager_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Product updated successfully.")
        return redirect("products:detail", pk=pk)
    return render(request, "products/form.html", {
        "title": "Edit Product", "form": form, "back_url": "products:list"
    })


@login_required
def product_detail(request, pk):
    product = get_object_or_404(product_queryset(), pk=pk)
    return render(request, "products/product_detail.html", {
        "title": product.name,
        "product": product,
        "can_manage": can_manage_products(request.user),
    })


@product_manager_required
def stock_transaction_create(request):
    form = StockTransactionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        from .inventory import record_stock_transaction
        try:
            record_stock_transaction(
                product_id=form.cleaned_data["product"].pk,
                transaction_type=form.cleaned_data["transaction_type"],
                quantity=form.cleaned_data["quantity"],
                user=request.user,
                reference=form.cleaned_data["reference"],
                remarks=form.cleaned_data["remarks"],
            )
        except Exception as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, "Stock transaction recorded successfully.")
            return redirect("products:stock")
    return render(request, "products/form.html", {
        "title": "Stock Transaction",
        "form": form,
        "back_url": "products:stock",
    })


@login_required
def stock_list(request):
    transactions = StockTransaction.objects.select_related(
        "product", "created_by"
    )
    query = request.GET.get("q", "").strip()
    if query:
        transactions = transactions.filter(
            product__name__icontains=query
        ) | transactions.filter(
            product__sku__icontains=query
        ) | transactions.filter(reference__icontains=query)
    return render(request, "products/stock.html", {
        "title": "Stock Management",
        "transactions": transactions.distinct(),
        "can_manage": can_manage_products(request.user),
    })
