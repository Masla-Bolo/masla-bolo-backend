from .common import MyApiOfficial, serializers


class OfficialSerializer(serializers.ModelSerializer):

    class Meta:
        model = MyApiOfficial
        fields = [
            "id",
            "user",
            "assigned_issues",
            "area_range",
            "city_name",
            "country_name",
            "district_name",
            "country_code",
        ]
        read_only_fields = ["area_range", "country_code"]
