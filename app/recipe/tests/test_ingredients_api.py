from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from rest_framework.test import APIClient

from rest_framework import status

from core.models import Ingredient, Recipe

from recipe.serializers import IngredientSerializer

INGREDIENTS_URL = reverse('recipe:ingredient-list')


class PublicIngredientApiTest(TestCase):
    """Test the public available ingredients API"""

    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        """Test that login is required for retrieving ingredients"""
        res = self.client.get(INGREDIENTS_URL)

        self.assertEquals(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientApi(TestCase):
    """Test the private ingredients API"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            'test@test.com',
            'password123'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredient_list(self):
        """Test retrieving a list of ingredients"""
        Ingredient.objects.create(user=self.user, name='Radish')
        Ingredient.objects.create(user=self.user, name="Lettuce")

        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEquals(res.status_code, status.HTTP_200_OK)
        self.assertEquals(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """Test that ingredients for the authenticated user are returned"""
        user2 = get_user_model().objects.create_user(
            'test2@test.com',
            'pass1234'
        )
        Ingredient.objects.create(user=user2, name='Chilli Powder')
        ingredient = Ingredient.objects.create(user=self.user, name='Salt')

        res = self.client.get(INGREDIENTS_URL)
        self.assertEquals(res.status_code, status.HTTP_200_OK)
        self.assertEquals(len(res.data), 1)
        self.assertEquals(res.data[0]['name'], ingredient.name)

    def test_create_ingredient_successfull(self):
        """Test create a new ingredient"""
        payload = {'name': 'Cabbage'}
        self.client.post(INGREDIENTS_URL, payload)

        exists = Ingredient.objects.filter(
            user=self.user,
            name=payload['name']
        ).exists()
        self.assertTrue(exists)

    def test_create_ingredient_invalid(self):
        """Test creating ingredient with invalid payload"""
        payload = {'name': ''}
        res = self.client.post(INGREDIENTS_URL, payload)

        self.assertEquals(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_ingredients_assigned_to_recipes(self):
        """Test filtering ingredients by those assigned to recipes"""
        ingredient1 = Ingredient.objects.create(user=self.user, name='Apples')
        ingredient2 = Ingredient.objects.create(user=self.user, name='Butter')
        recipe = Recipe.objects.create(
            title='Apple Crumble',
            time_minutes=40,
            price=20,
            user=self.user
        )
        recipe.ingredients.add(ingredient1)
        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})
        serializer1 = IngredientSerializer(ingredient1)
        serializer2 = IngredientSerializer(ingredient2)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_retrieve_ingredients_assigned_unique(self):
        """Test filtering ingredients by assigned returned unique items"""
        ingredient = Ingredient.objects.create(user=self.user, name='Eggs')
        Ingredient.objects.create(user=self.user, name='Brown Sugar')
        recipe1 = Recipe.objects.create(
            title='Apple Pie',
            time_minutes=33,
            price=20,
            user=self.user
        )
        recipe1.ingredients.add(ingredient)
        recipe2 = Recipe.objects.create(
            title='Cheesy Noodles',
            time_minutes=12,
            price=5,
            user=self.user
        )
        recipe2.ingredients.add(ingredient)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})
        self.assertEqual(len(res.data), 1)
