import base64
import csv
import os
import uuid
from io import StringIO
from fpdf import FPDF

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import redirect
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from api.abstractions.views import handle_recipe_operation
from api.fields import Base62Field
from api.filters import RecipeFilter
from api.paginations import Pagination
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (FavoriteSerializer, FollowSerializer,
                             IngredientSerializer, RecipeReadSerializer,
                             RecipeWriteSerializer, ShoppingCartSerializer,
                             SubscriptionSerializer, UserSerializer)
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart)
from users.models import Follow

User = get_user_model()


class UserViewSet(DjoserUserViewSet):
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    pagination_class = Pagination
    permission_classes = [permissions.AllowAny]

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def get_current_user(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['put', 'delete'],
        permission_classes=[permissions.IsAuthenticated],
        url_path='me/avatar'
    )
    def handle_avatar(self, request):
        user = request.user

        if request.method == 'PUT':
            avatar_data = request.data.get('avatar')
            if not avatar_data:
                return Response(
                    {"avatar": ["Это поле обязательно."]},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                # Удаляем старый аватар, если есть
                if user.avatar:
                    if os.path.exists(user.avatar.path):
                        os.remove(user.avatar.path)
                    user.avatar.delete()

                # Обрабатываем новое изображение
                format, imgstr = avatar_data.split(';base64,')
                ext = format.split('/')[-1]
                data = ContentFile(base64.b64decode(imgstr), name=f"{uuid.uuid4()}.{ext}")

                # Сохраняем новый аватар
                user.avatar.save(data.name, data, save=True)
                avatar_url = request.build_absolute_uri(user.avatar.url)
                return Response({"avatar": avatar_url}, status=status.HTTP_200_OK)

            except Exception as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Удаление аватара
        if user.avatar:
            avatar_path = user.avatar.path
            if os.path.exists(avatar_path):
                os.remove(avatar_path)
            user.avatar.delete()
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(
            {"detail": "Аватар отсутствует."},
            status=status.HTTP_404_NOT_FOUND
        )

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='subscribe',
        permission_classes=[permissions.IsAuthenticated]
    )
    def manage_follow(self, request, id=None):
        user = request.user

        if request.method == 'POST':
            serializer = SubscriptionSerializer(
                data={'following_id': id},
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            follow = serializer.save()
            return Response(
                FollowSerializer(
                    follow.following,
                    context={'request': request}
                ).data,
                status=status.HTTP_201_CREATED
            )

        following_user = get_object_or_404(User, pk=id)
        follow_instance = Follow.objects.filter(
            user=user,
            following=following_user
        ).first()

        if not follow_instance:
            return Response(
                {"detail": "Вы не подписаны на этого пользователя."},
                status=status.HTTP_400_BAD_REQUEST
            )

        follow_instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        url_path='subscriptions',
        permission_classes=[permissions.IsAuthenticated]
    )
    def list_subscriptions(self, request):
        user = request.user
        subscriptions = User.objects.filter(following__user=user)
        page = self.paginate_queryset(subscriptions)
        serializer = FollowSerializer(
            page,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all().select_related('author').prefetch_related('ingredients')
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsAuthorOrReadOnly
    ]
    pagination_class = Pagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RecipeWriteSerializer
        return RecipeReadSerializer

    @action(
        detail=True,
        methods=["get"],
        url_path="get-link",
        permission_classes=[permissions.AllowAny]
    )
    def generate_share_link(self, request, pk=None):
        recipe = self.get_object()
        short_code = Base62Field.to_base62(recipe.id)
        short_link = request.build_absolute_uri(f"/s/{short_code}")
        return Response({"short-link": short_link}, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['get'],
        url_path='download_shopping_cart',
        permission_classes=[permissions.IsAuthenticated]
    )
    def export_shopping_cart(self, request):
        # Получаем список ингредиентов
        ingredients = (
            RecipeIngredient.objects
            .filter(recipe__shopping_carts__user=request.user)
            .values(
                'ingredient__name',
                'ingredient__measurement_unit'
            )
            .annotate(total_amount=Sum('amount'))
            .order_by('ingredient__name')
        )

        ingredients_list = [
            {
                'name': item['ingredient__name'],
                'amount': item['total_amount'],
                'measurement_unit': item['ingredient__measurement_unit']
            }
            for item in ingredients
        ]

        file_format = request.query_params.get('format', 'txt').lower()

        if file_format == 'txt':
            return self._generate_text_response(ingredients_list)
        elif file_format == 'csv':
            return self._generate_csv_response(ingredients_list)
        elif file_format == 'pdf':
            return self._generate_pdf_response(ingredients_list)
        else:
            return Response(
                {"detail": "Неподдерживаемый формат файла"},
                status=status.HTTP_400_BAD_REQUEST
            )

    def _generate_text_response(self, ingredients):
        content = "\n".join(
            f"{item['name']} ({item['measurement_unit']}) — {item['amount']}"
            for item in ingredients
        )
        response = HttpResponse(content, content_type="text/plain")
        response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
        return response

    def _generate_csv_response(self, ingredients):
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Ингредиент', 'Количество', 'Единица измерения'])

        for item in ingredients:
            writer.writerow([
                item['name'],
                item['amount'],
                item['measurement_unit']
            ])

        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response['Content-Disposition'] = 'attachment; filename="shopping_list.csv"'
        return response

    def _generate_pdf_response(self, ingredients):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Список покупок", ln=True, align='C')

        for item in ingredients:
            pdf.cell(
                200,
                10,
                txt=f"{item['name']} ({item['measurement_unit']}) — {item['amount']}",
                ln=True
            )

        response = HttpResponse(
            pdf.output(dest='S').encode('latin1'),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = 'attachment; filename="shopping_list.pdf"'
        return response

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='favorite',
        permission_classes=[permissions.IsAuthenticated]
    )
    def manage_favorite(self, request, pk=None):
        return handle_recipe_operation(
            request, pk, Favorite, FavoriteSerializer
        )

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='shopping_cart',
        permission_classes=[permissions.IsAuthenticated]
    )
    def manage_shopping_cart(self, request, pk=None):
        return handle_recipe_operation(
            request, pk, ShoppingCart, ShoppingCartSerializer
        )


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (SearchFilter,)
    search_fields = ['name']
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__istartswith=name)
        return queryset