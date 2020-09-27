from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required
from juniper.app.product import bp
from juniper.app.product.forms import ProductForm
from juniper.app.product.models import Product, PriceSpecification
from juniper.app import db


@bp.route('/list', methods=['GET'])
@login_required
def list_products():

    products = db.session.query(Product).all()

    return render_template('product/list.html',
                           products=products)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_product():
    form = ProductForm()

    if form.validate_on_submit():
        product = Product()

        product.name = form.name.data
        product.category = 'TICKET'
        product.description = form.description.data

        price_spec = PriceSpecification()
        price_spec.price = form.price.data
        price_spec.flat_fee = 0.00
        price_spec.cost_fee = 0.00

        product.price_specification = price_spec

        db.session.add(product)
        db.session.commit()

        flash('Product added', 'success')

        return redirect(url_for('products.list_products'))

    return render_template('product/add.html', form=form)