from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kg", "0002_reference_citations_count_and_more"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="triple",
            index=models.Index(
                fields=["-confidence", "-support_count", "id"],
                name="triple_conf_support_id_idx",
            ),
        ),
    ]
