from django.core.management import execute_from_command_line


def dev():
    execute_from_command_line(
        ["manage.py", "runserver", "--settings=EasyTPCloud.settings.development"]
    )
