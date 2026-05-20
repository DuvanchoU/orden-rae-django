from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='PagoStripe',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_intent_id', models.CharField(db_index=True, max_length=255, unique=True)),
                ('payment_method_id', models.CharField(blank=True, max_length=255, null=True)),
                ('checkout_session_id', models.CharField(blank=True, db_index=True, max_length=255, null=True)),
                ('venta_id', models.IntegerField(blank=True, null=True)),
                ('pedido_id', models.IntegerField(blank=True, null=True)),
                ('cliente_id', models.IntegerField(blank=True, null=True)),
                ('monto', models.BigIntegerField(help_text='Monto en centavos COP')),
                ('monto_reembolsado', models.BigIntegerField(default=0)),
                ('moneda', models.CharField(default='cop', max_length=3)),
                ('estado', models.CharField(
                    choices=[
                        ('PENDIENTE', 'Pendiente'),
                        ('COMPLETADO', 'Completado'),
                        ('FALLIDO', 'Fallido'),
                        ('CANCELADO', 'Cancelado'),
                        ('REEMBOLSADO', 'Reembolsado'),
                    ],
                    db_index=True,
                    default='PENDIENTE',
                    max_length=12,
                )),
                ('descripcion', models.TextField(blank=True, null=True)),
                ('metadata_json', models.TextField(blank=True, null=True, help_text='JSON extra enviado a Stripe')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('confirmed_at', models.DateTimeField(blank=True, null=True)),
                ('failed_at', models.DateTimeField(blank=True, null=True)),
                ('error_code', models.CharField(blank=True, max_length=100, null=True)),
                ('error_message', models.TextField(blank=True, null=True)),
            ],
            options={
                'db_table': 'pagos_stripe',
                'ordering': ['-created_at'],
            },
        ),
    ]