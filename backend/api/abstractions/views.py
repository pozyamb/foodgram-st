from rest_framework import status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from recipes.models import Recipe


def handle_recipe_operation(request, pk, model, serializer_class):
    recipe = get_object_or_404(Recipe, pk=pk)

    if request.method == 'POST':
        serializer = serializer_class(
            data={
                'user': request.user.id,
                'recipe': recipe.id
            },
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    item = model.objects.filter(
        user=request.user,
        recipe=recipe
    ).first()

    if not item:
        return Response(
            {"detail": f"Рецепт не найден в {model._meta.verbose_name}."},
            status=status.HTTP_400_BAD_REQUEST
        )

    item.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)