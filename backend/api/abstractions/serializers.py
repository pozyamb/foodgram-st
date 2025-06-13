from rest_framework import serializers


class BaseUserRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ['user', 'recipe']

    def validate(self, data):
        user = data['user']
        recipe = data['recipe']
        if self.Meta.model.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(
                f"Рецепт уже есть в {self.Meta.model._meta.verbose_name}."
            )
        return data

    def to_representation(self, instance):
        from api.serializers import ShortRecipeSerializer
        return ShortRecipeSerializer(instance.recipe).data