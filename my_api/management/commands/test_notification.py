from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from my_api.models import Issue, Notification
from my_api.utils import send_push_notification 

User = get_user_model()

class Command(BaseCommand):
    help = 'Test background push notifications by simulating a like action'

    def add_arguments(self, parser):
        parser.add_argument('--user_id', type=int, help='User ID who will perform the like action')
        parser.add_argument('--issue_id', type=int, help='Issue ID to be liked')

    def handle(self, *args, **options):
        try:
            user_id = options['user_id']
            issue_id = options['issue_id']

            try:
                user = User.objects.get(id=user_id)
                issue = Issue.objects.get(id=issue_id)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User with ID {user_id} does not exist'))
                return
            except Issue.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Issue with ID {issue_id} does not exist'))
                return
            
            notification = Notification.objects.create(
                user=user,
                screen="issueDetail",
                screen_id=issue.id,
                title="Background Issue Testing Again!!",
                description="This is a test for background and terminated Notification!!!"
            )

            send_push_notification(notification)

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created like and sent notification:\n'
                    f'User: {user.username}\n'
                    f'Issue: {issue.id}\n'
                    f'Notification ID: {notification.id}'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error occurred: {str(e)}')
            )