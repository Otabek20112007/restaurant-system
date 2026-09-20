from django import forms
from apps.models import Category, MenuItem


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'printer_target', 'sort_order']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Пицца'
            }),
            'printer_target': forms.Select(attrs={'class': 'form-select'}),
            'sort_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0'
            }),
        }
        labels = {
            'name': 'Название',
            'printer_target': 'Куда печатать',
            'sort_order': 'Порядок сортировки',
        }


class MenuItemForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = [
            'name', 'category', 'price', 'description',
            'weight', 'image', 'is_available'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Маргарита'
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '550'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Состав, особенности...'
            }),
            'weight': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '450'
            }),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'Название',
            'category': 'Категория',
            'price': 'Цена (сом)',
            'description': 'Описание',
            'weight': 'Вес (г)',
            'image': 'Фото',
            'is_available': 'Доступно для заказа',
        }
    
    def __init__(self, *args, **kwargs):
        restaurant = kwargs.pop('restaurant', None)
        super().__init__(*args, **kwargs)
        
        # Показываем только категории этого ресторана
        if restaurant:
            self.fields['category'].queryset = Category.objects.filter(
                restaurant=restaurant
            )