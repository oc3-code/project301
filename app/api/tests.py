import unittest
from decimal import Decimal

from django.contrib.auth.hashers import check_password
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Order, OrderProduct, Product, Shipment, User, UserType


class BaseAPITestCase(APITestCase):
    """Creates one of each entity so tests can focus on behaviour."""

    def setUp(self):
        self.user_type = UserType.objects.create(code="ADMIN", description="Administrator")
        self.user = User.objects.create(
            name="Alice", login="alice", password="x", user_type=self.user_type
        )
        self.product = Product.objects.create(
            sku="SKU-1", description="Widget", unit_price=Decimal("10.00")
        )
        self.product2 = Product.objects.create(
            sku="SKU-2", description="Gadget", unit_price=Decimal("20.50")
        )
        self.order = Order.objects.create(user=self.user)
        self.item = OrderProduct.objects.create(
            order=self.order, product=self.product, quantity=2, sale_price=Decimal("9.50")
        )
        self.shipment = Shipment.objects.create(
            carrier="UPS", tracking_number="1Z999", order=self.order
        )

    def post(self, name, data, *args):
        return self.client.post(reverse(name, args=args), data, format="json")

    def put(self, name, data, *args):
        return self.client.put(reverse(name, args=args), data, format="json")

    def patch(self, name, data, *args):
        return self.client.patch(reverse(name, args=args), data, format="json")


# --------------------------------------------------------------------------
# UserType
# --------------------------------------------------------------------------
class UserTypeAPITests(BaseAPITestCase):
    def test_list(self):
        r = self.client.get(reverse("usertype-list"))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 1)

    def test_create(self):
        r = self.post("usertype-list", {"code": "CUST", "description": "Customer"})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertTrue(UserType.objects.filter(code="CUST").exists())

    def test_create_duplicate_code(self):
        r = self.post("usertype-list", {"code": "ADMIN", "description": "dup"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code", r.data)

    def test_create_missing_fields(self):
        r = self.post("usertype-list", {})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_and_404(self):
        r = self.client.get(reverse("usertype-detail", args=[self.user_type.pk]))
        self.assertEqual(r.data["code"], "ADMIN")
        r = self.client.get(reverse("usertype-detail", args=[9999]))
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_and_patch(self):
        r = self.put("usertype-detail", {"code": "ROOT", "description": "Root"}, self.user_type.pk)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        r = self.patch("usertype-detail", {"description": "Changed"}, self.user_type.pk)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.user_type.refresh_from_db()
        self.assertEqual((self.user_type.code, self.user_type.description), ("ROOT", "Changed"))

    def test_put_missing_field(self):
        r = self.put("usertype-detail", {"code": "ROOT"}, self.user_type.pk)
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_unused(self):
        ut = UserType.objects.create(code="TMP", description="tmp")
        r = self.client.delete(reverse("usertype-detail", args=[ut.pk]))
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_in_use_is_protected(self):
        # Currently surfaces as an unhandled ProtectedError (HTTP 500 in production).
        # If the view is changed to return 409/400, update this assertion.
        with self.assertRaises(ProtectedError):
            self.client.delete(reverse("usertype-detail", args=[self.user_type.pk]))
        self.assertTrue(UserType.objects.filter(pk=self.user_type.pk).exists())


# --------------------------------------------------------------------------
# User
# --------------------------------------------------------------------------
class UserAPITests(BaseAPITestCase):
    def payload(self, **kw):
        data = {"name": "Bob", "login": "bob", "password": "s3cret", "user_type": self.user_type.pk}
        data.update(kw)
        return data

    def test_list_hides_password(self):
        r = self.client.get(reverse("user-list"))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertNotIn("password", r.data[0])

    def test_create_hashes_password_and_hides_it(self):
        r = self.post("user-list", self.payload())
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", r.data)
        stored = User.objects.get(login="bob").password
        self.assertNotEqual(stored, "s3cret")
        self.assertTrue(check_password("s3cret", stored))

    def test_create_duplicate_login(self):
        r = self.post("user-list", self.payload(login="alice"))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("login", r.data)

    def test_create_invalid_user_type(self):
        r = self.post("user-list", self.payload(user_type=9999))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("user_type", r.data)

    def test_create_missing_password(self):
        data = self.payload()
        del data["password"]
        r = self.post("user-list", data)
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_and_404(self):
        r = self.client.get(reverse("user-detail", args=[self.user.pk]))
        self.assertEqual(r.data["login"], "alice")
        self.assertNotIn("password", r.data)
        self.assertEqual(
            self.client.get(reverse("user-detail", args=[9999])).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_patch_name(self):
        r = self.patch("user-detail", {"name": "Alicia"}, self.user.pk)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, "Alicia")

    @unittest.expectedFailure
    def test_update_hashes_password(self):
        # KNOWN BUG: UserSerializer only hashes in create(), so updates store plaintext.
        # Remove @expectedFailure once update() is fixed.
        self.patch("user-detail", {"password": "newpass"}, self.user.pk)
        self.user.refresh_from_db()
        self.assertTrue(check_password("newpass", self.user.password))

    def test_delete_user_without_orders(self):
        u = User.objects.create(name="T", login="t", password="x", user_type=self.user_type)
        r = self.client.delete(reverse("user-detail", args=[u.pk]))
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_user_with_orders_is_protected(self):
        with self.assertRaises(ProtectedError):
            self.client.delete(reverse("user-detail", args=[self.user.pk]))
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())


# --------------------------------------------------------------------------
# Product
# --------------------------------------------------------------------------
class ProductAPITests(BaseAPITestCase):
    def test_list(self):
        r = self.client.get(reverse("product-list"))
        self.assertEqual(len(r.data), 2)

    def test_create(self):
        r = self.post("product-list", {"sku": "SKU-3", "description": "Thing", "unit_price": "5.25"})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.get(sku="SKU-3").unit_price, Decimal("5.25"))

    def test_create_duplicate_sku(self):
        r = self.post("product-list", {"sku": "SKU-1", "description": "d", "unit_price": "1.00"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("sku", r.data)

    def test_create_too_many_decimals(self):
        r = self.post("product-list", {"sku": "S", "description": "d", "unit_price": "1.234"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("unit_price", r.data)

    def test_create_non_numeric_price(self):
        r = self.post("product-list", {"sku": "S", "description": "d", "unit_price": "abc"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_fields(self):
        r = self.post("product-list", {"sku": "S"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_and_404(self):
        r = self.client.get(reverse("product-detail", args=[self.product.pk]))
        self.assertEqual(r.data["sku"], "SKU-1")
        self.assertEqual(
            self.client.get(reverse("product-detail", args=[9999])).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_put_and_patch(self):
        r = self.put(
            "product-detail",
            {"sku": "SKU-1", "description": "New", "unit_price": "11.00"},
            self.product.pk,
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        r = self.patch("product-detail", {"unit_price": "12.00"}, self.product.pk)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.description, "New")
        self.assertEqual(self.product.unit_price, Decimal("12.00"))

    def test_delete_unused(self):
        r = self.client.delete(reverse("product-detail", args=[self.product2.pk]))
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_in_use_is_protected(self):
        with self.assertRaises(ProtectedError):
            self.client.delete(reverse("product-detail", args=[self.product.pk]))


# --------------------------------------------------------------------------
# Order
# --------------------------------------------------------------------------
class OrderAPITests(BaseAPITestCase):
    def test_list(self):
        r = self.client.get(reverse("order-list"))
        self.assertEqual(len(r.data), 1)

    def test_create_defaults_created(self):
        r = self.post("order-list", {"user": self.user.pk})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(r.data["created"])
        self.assertEqual(Order.objects.count(), 2)

    def test_create_invalid_user(self):
        r = self.post("order-list", {"user": 9999})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_user(self):
        r = self.post("order-list", {})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_and_404(self):
        r = self.client.get(reverse("order-detail", args=[self.order.pk]))
        self.assertEqual(r.data["user"], self.user.pk)
        self.assertEqual(
            self.client.get(reverse("order-detail", args=[9999])).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_delete_cascades_to_items_and_shipment(self):
        r = self.client.delete(reverse("order-detail", args=[self.order.pk]))
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(OrderProduct.objects.count(), 0)
        self.assertEqual(Shipment.objects.count(), 0)


# --------------------------------------------------------------------------
# OrderProduct
# --------------------------------------------------------------------------
class OrderProductAPITests(BaseAPITestCase):
    def test_list(self):
        r = self.client.get(reverse("order-product-list"))
        self.assertEqual(len(r.data), 1)

    def test_create(self):
        r = self.post(
            "order-product-list",
            {"order": self.order.pk, "product": self.product2.pk, "quantity": 1, "sale_price": "20.00"},
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.order.items.count(), 2)

    def test_create_duplicate_order_product(self):
        # KNOWN GAP: DRF 3.12 does not validate UniqueConstraint, so the DB error
        # escapes as an unhandled IntegrityError (HTTP 500). Ideally the serializer
        # would return 400; if so, replace this with a 400 status assertion.
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.post(
                "order-product-list",
                {"order": self.order.pk, "product": self.product.pk, "quantity": 1, "sale_price": "1.00"},
            )
        self.assertEqual(self.order.items.count(), 1)

    def test_create_invalid_refs_and_values(self):
        base = {"order": self.order.pk, "product": self.product2.pk, "quantity": 1, "sale_price": "1.00"}
        for bad in ({"order": 9999}, {"product": 9999}, {"quantity": "abc"}, {"sale_price": "1.234"}):
            with self.subTest(bad=bad):
                r = self.post("order-product-list", {**base, **bad})
                self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_patch_delete_by_pk(self):
        url = reverse("order-product-detail", args=[self.item.pk])
        self.assertEqual(self.client.get(url).data["quantity"], 2)
        r = self.client.patch(url, {"quantity": 5}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 5)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)

    # --- GET orderproduct/order/<order_id> ---------------------------------
    def test_items_by_order(self):
        other = Order.objects.create(user=self.user)
        OrderProduct.objects.create(order=other, product=self.product2, quantity=1, sale_price=Decimal("1"))
        r = self.client.get(reverse("order-product-list-by-order", args=[self.order.pk]))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.json()), 1)
        self.assertEqual(r.json()[0]["product"], self.product.pk)

    def test_items_by_order_empty(self):
        other = Order.objects.create(user=self.user)
        r = self.client.get(reverse("order-product-list-by-order", args=[other.pk]))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.json(), [])

    def test_items_by_order_unknown_order(self):
        r = self.client.get(reverse("order-product-list-by-order", args=[9999]))
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_items_by_order_post_not_allowed(self):
        r = self.post("order-product-list-by-order", {}, self.order.pk)
        self.assertEqual(r.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # --- order/<o>/product/<p> ---------------------------------------------
    def keys_url(self, order_id=None, product_id=None):
        return reverse(
            "order-product-detail-by-keys",
            args=[order_id or self.order.pk, product_id or self.product.pk],
        )

    def test_keys_patch_quantity_only(self):
        r = self.client.patch(self.keys_url(), {"quantity": 7}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 7)
        self.assertEqual(self.item.sale_price, Decimal("9.50"))

    def test_keys_patch_price_only(self):
        r = self.client.patch(self.keys_url(), {"sale_price": "8.00"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.item.refresh_from_db()
        self.assertEqual(self.item.sale_price, Decimal("8.00"))
        self.assertEqual(self.item.quantity, 2)

    def test_keys_put_both(self):
        r = self.client.put(self.keys_url(), {"quantity": 3, "sale_price": "7.00"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.item.refresh_from_db()
        self.assertEqual((self.item.quantity, self.item.sale_price), (3, Decimal("7.00")))

    def test_keys_no_updatable_fields(self):
        r = self.client.patch(self.keys_url(), {"foo": "bar"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_keys_cannot_change_order_or_product(self):
        other = Order.objects.create(user=self.user)
        r = self.client.patch(
            self.keys_url(),
            {"quantity": 4, "order": other.pk, "product": self.product2.pk},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.item.refresh_from_db()
        self.assertEqual(self.item.order_id, self.order.pk)
        self.assertEqual(self.item.product_id, self.product.pk)

    def test_keys_invalid_value(self):
        r = self.client.patch(self.keys_url(), {"quantity": "abc"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_keys_unknown_pair(self):
        r = self.client.patch(self.keys_url(product_id=self.product2.pk), {"quantity": 1}, format="json")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_keys_delete_then_404(self):
        self.assertEqual(self.client.delete(self.keys_url()).status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(OrderProduct.objects.filter(pk=self.item.pk).exists())
        self.assertEqual(self.client.delete(self.keys_url()).status_code, status.HTTP_404_NOT_FOUND)

    def test_keys_get_not_allowed(self):
        self.assertEqual(self.client.get(self.keys_url()).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


# --------------------------------------------------------------------------
# Shipment
# --------------------------------------------------------------------------
class ShipmentAPITests(BaseAPITestCase):
    def test_list(self):
        r = self.client.get(reverse("shipment-list"))
        self.assertEqual(len(r.data), 1)

    def test_create_defaults_shipped(self):
        order2 = Order.objects.create(user=self.user)
        r = self.post("shipment-list", {"carrier": "DHL", "tracking_number": "T1", "order": order2.pk})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(r.data["shipped"])

    def test_create_second_shipment_for_same_order(self):
        r = self.post(
            "shipment-list",
            {"carrier": "DHL", "tracking_number": "T2", "order": self.order.pk},
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("order", r.data)

    def test_create_invalid_order_or_missing_fields(self):
        r = self.post("shipment-list", {"carrier": "DHL", "tracking_number": "T", "order": 9999})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        r = self.post("shipment-list", {})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_and_404(self):
        r = self.client.get(reverse("shipment-detail", args=[self.shipment.pk]))
        self.assertEqual(r.data["carrier"], "UPS")
        self.assertEqual(
            self.client.get(reverse("shipment-detail", args=[9999])).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_patch_and_delete(self):
        r = self.patch("shipment-detail", {"carrier": "FedEx"}, self.shipment.pk)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.shipment.refresh_from_db()
        self.assertEqual(self.shipment.carrier, "FedEx")
        r = self.client.delete(reverse("shipment-detail", args=[self.shipment.pk]))
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------
# Cross-cutting
# --------------------------------------------------------------------------
class GeneralAPITests(BaseAPITestCase):
    def test_post_to_detail_not_allowed(self):
        r = self.post("product-detail", {}, self.product.pk)
        self.assertEqual(r.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_malformed_json(self):
        r = self.client.post(
            reverse("product-list"), data="{not json", content_type="application/json"
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_detail_url_requires_no_trailing_slash(self):
        r = self.client.get(reverse("product-detail", args=[self.product.pk]) + "/")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)
