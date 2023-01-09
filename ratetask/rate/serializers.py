from rest_framework import serializers
from rest_framework.exceptions import ValidationError


class RatesListSerializer(serializers.Serializer):
    day = serializers.DateField(source="generated_day")
    average_price = serializers.IntegerField(allow_null=True)

    class Meta:
        read_only = True


class RatesListValidator(serializers.Serializer):
    date_from = serializers.DateField(required=True, input_formats=["%Y-%m-%d"])
    date_to = serializers.DateField(required=True, input_formats=["%Y-%m-%d"])
    origin = serializers.CharField(min_length=5, required=True)
    destination = serializers.CharField(min_length=5, required=True)

    def validate(self, params):
        """non-specific field validation"""
        if params["date_from"] > params["date_to"]:
            raise ValidationError(detail="`date_from` cannot be before `date_to`")

        # client cannot query more than 60 days of data
        if (params["date_to"] - params["date_from"]).days > 60:
            raise ValidationError(detail="The allowed interval is 60 days")

        return params
