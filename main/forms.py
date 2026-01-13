import re
from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import DefaultUser, AccessGroup, App, UsersFromCSV
from django.core.validators import FileExtensionValidator
from .custom_validators import validate_file_size
from django.contrib.auth import get_user_model
from .models import UserActivity

class UsersFromCSVForm(forms.ModelForm):
    class Meta:
        model = UsersFromCSV
        fields = "__all__"
        help_texts = {
            'file': 'Upload a CSV (or excel) file containing emails of new users, emails must end with "@esi.dz"',
            'role': 'Specify the role of new users',
            'group': 'Specify the access group of new users'
        }


class CustomUserCreationForm(UserCreationForm):
    role = forms.ChoiceField(label='Role', choices=DefaultUser.ROLES, required=True)
    group = forms.ModelChoiceField(AccessGroup.objects.all(), label='group', required=True)

    class Meta:
        model = DefaultUser
        fields = ("username", "email")


class PublicUserCreationForm(UserCreationForm):
    """Form for public signup with default role and group"""
    email = forms.EmailField(required=True, help_text="Adresse email obligatoire")
    username = forms.CharField(
        required=True,
        help_text="Required. Only letters, numbers, dots (.) and hyphens (-) are allowed."
    )
    
    class Meta:
        model = DefaultUser
        fields = ("username", "email", "password1", "password2")
        
    def clean_username(self):
        username = self.cleaned_data['username']
        # Regular expression to allow only letters, numbers, dots and hyphens
        if not re.match(r'^[\w.-]+$', username):
            raise forms.ValidationError(
                "Username can only contain letters, numbers, dots (.) and hyphens (-)."
            )
        return username
        
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        
        # Set default role and group for public signups
        user.role = 'S'  # Change this to your default role value
        
        if commit:
            # Set default group after user is saved (if it's a many-to-many relationship)
            try:
                
                default_group, _created = AccessGroup.objects.get_or_create(
                    name=AccessGroup.GUEST,
                    defaults={'name': 'Guest'}
                )

                user.group = default_group
                user.save()
                return user
            except AccessGroup.DoesNotExist:
                # Handle case where default group doesn't exist
                raise forms.ValidationError("Default access group 'Guest' does not exist.")

class CustomAppForm(forms.ModelForm):
    class Meta:
        model = App
        fields = "__all__"
        widgets = {"group": forms.CheckboxSelectMultiple}

    # add every new app to FULL ACCESS GROUP
    def clean_group(self):
        data = self.cleaned_data['group']
        AccessGroup.objects.get_or_create(name=AccessGroup.FULL)
        fag = AccessGroup.objects.filter(name=AccessGroup.FULL)
        data |= fag

        return data


class CustomChangeAccessGroup(forms.ModelForm):
    apps = forms.ModelMultipleChoiceField(queryset=App.objects.all(), required=True,
                                          help_text='Choose which apps to give access to',
                                          widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, **kwargs):
        super(CustomChangeAccessGroup, self).__init__(*args, **kwargs)
        group = kwargs['instance']
        self.fields['apps'].initial = [app for app in group.apps.all()]

    def save(self, commit=True):
        instance = super().save(commit=False)

        apps = self.cleaned_data['apps']

        instance.save()
        instance.apps.set(apps)

        return instance

    class Meta:
        model = AccessGroup
        fields = "__all__"


class CustomAddAccessGroup(forms.ModelForm):
    name = forms.ChoiceField(choices=[('add_new', 'ADD New')] + AccessGroup.GROUPS,
                             label="Legacy access groups",
                             help_text='choose legacy group from list')
    add_new = forms.CharField(max_length=25, required=False,
                              help_text='to add a new group select ADD NEW in legacy group',
                              label='Add new group')

    apps = forms.ModelMultipleChoiceField(queryset=App.objects.all(), required=False,
                                          help_text='Choose which apps to give access to',
                                          widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, **kwargs):
        data = args[0] if args else kwargs.get('data', None)
        super(CustomAddAccessGroup, self).__init__(*args, **kwargs)
        if data:
            if 'add_new' in data and data.get('name') == 'add_new' and data.get('add_new'):
                _mutable = data._mutable
                data._mutable = True
                data['name'] = data['add_new']  # Use 'add_new' instead of 'other'
                data._mutable = _mutable
                self.fields['name'].choices += [(data['add_new'], data['add_new'])]

    def save(self, commit=True):
        instance = super().save(commit=False)

        apps = self.cleaned_data['apps']

        instance.save()
        instance.apps.set(apps)

        return instance
    
    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('name') == 'add_new' and cleaned_data.get('add_new'):
            new_name = cleaned_data['add_new']
            if AccessGroup.objects.filter(name=new_name).exists():
                raise forms.ValidationError("An access group with this name already exists.")
        return cleaned_data

    class Meta:
        model = AccessGroup
        fields = "__all__"


class UploadFileForm(forms.Form):
    file = forms.FileField(max_length=1000, validators=[validate_file_size], label="Upload file here")


class ActivityFilterForm(forms.Form):
    """Form for filtering user activities"""
    
    user = forms.ModelChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        empty_label="All Users"
    )
    
    activity_type = forms.ChoiceField(
        choices=[('', 'All Activities')] + UserActivity.ACTIVITY_CHOICES,
        required=False
    )
    
    start_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
    )
    
    end_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})
