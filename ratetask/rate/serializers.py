from rest_framework import serializers


class RatesListSerializer(serializers.Serializer):
    day = serializers.DateField(source="generated_day")
    average_price = serializers.IntegerField(allow_null=True)
    c = serializers.IntegerField()

    class Meta:
        read_only = True


class RatesListValidator(serializers.Serializer):
    date_from = serializers.DateField(required=True, input_formats=["%Y-%m-%d"])
    date_to = serializers.DateField(required=True, input_formats=["%Y-%m-%d"])
    origin = serializers.CharField(min_length=5, required=True)
    destination = serializers.CharField(min_length=5, required=True)

    # TODO: validate date_from is always behind date_to
    # TODO: validate the from/to range is not more than 2 months
