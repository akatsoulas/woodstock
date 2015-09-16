import re

from django.contrib import admin
from django.core.validators import EmailValidator
from django.forms import ValidationError

from import_export.admin import ExportMixin, ImportExportMixin
from import_export import fields, resources

from woodstock.voting.models import (Application, Event, PreferredEvent,
                                     MozillianGroup, MozillianProfile, Vote)
from woodstock.voting.utils import get_object_or_none, update_mozillian_profiles


USERNAME_RGX = re.compile('.+/u/(.+)(/)?')
UPLOAD_PATH_RGX = re.compile('.+\((.+)\)')


def get_mozillian_username(row):
    """Check if there is a mozillian username in each row."""

    username = ''
    if ('mozillian_username' not in row or
        'application_complete' not in row or
            row['application_complete'] == u'0'):
        return username

    # Normalize usernames
    username = row['mozillian_username']
    match = USERNAME_RGX.match(row['mozillian_username'])
    if match:
        username = match.groups()[0].strip('/')
    return username


class ApplicationResource(resources.ModelResource):

    class Meta:
        model = Application
        fields = ('entry_id', 'number_of_events', 'event', 'reasoning',
                  'impact', 'learning_areas', 'ideas', 'commitment_1',
                  'functional_team', 'team_contact',
                  'participation_opportunities', 'commitment_2',
                  'community', 'track_record', 'community_impact',
                  'commitment_3', 'other', 'application_complete', 'date',
                  'recommendation_letter',)
        import_id_fields = ('entry_id',)
        report_skipped = True

    # Import section
    def before_import(self, dataset, dry_run, **kwargs):
        """Override method for custom functionality."""

        # Normalize dataset
        if dataset.headers:
            dataset.headers = [unicode(header).lower().strip()
                               for header in dataset.headers]

    def get_or_init_instance(self, instance_loader, row):
        """Override method for custom functionality."""

        # If there isn't a username or the application is not complete,
        # do not return an instance.
        row['mozillian_username'] = get_mozillian_username(row)
        profile = get_object_or_none(
            MozillianProfile, mozillian_username=row['mozillian_username'])
        # If there is no profile force a skip
        if not profile:
            row['mozillian_username'] = ''

        # Normalize Dataset to db related fields
        event_headers = [e for e in row if 'event_' in e]
        events = [name for name in event_headers if row[name]]
        row['number_of_events'] = unicode(len(events))
        path_match = UPLOAD_PATH_RGX.match(row['recommendation_letter'])
        if path_match:
            row['recommendation_letter'] = path_match.groups()[0]

        return (super(ApplicationResource, self)
                .get_or_init_instance(instance_loader, row))

    def save_instance(self, instance, dry_run):
        if not dry_run:
            super(ApplicationResource, self).save_instance(instance, dry_run)

    def save_m2m(self, obj, data, dry_run):
        """Override save_m2m for custom functionality."""
        event_headers = [e for e in data if 'event_' in e]
        events = [name for name in event_headers if data[name]]

        for event_name in events:
            for event in Event.objects.all():
                if event.name in data[event_name]:
                    preferred = False
                    if event.name in data['preferred']:
                        preferred = True
                    if not PreferredEvent.objects.filter(
                            event=event, application=obj).exists():
                        PreferredEvent.objects.create(event=event,
                                                      application=obj,
                                                      preferred=preferred)
                    break
                continue

        super(ApplicationResource, self).save_m2m(obj, data, dry_run)


class EventResource(resources.ModelResource):

    class Meta:
        model = Event
        fields = ('name',)
        skip_unchanged = True
        report_skipped = True


class PreferredEventResource(resources.ModelResource):

    class Meta:
        model = PreferredEvent
        fields = ('event', 'application', 'preferred',)
        skip_unchanged = True
        report_skipped = True


class MozillianGroupResouce(resources.ModelResource):
    negative_votes = fields.Field()
    skip_votes = fields.Field()
    positive_votes = fields.Field()
    stellar_votes = fields.Field()
    total_votes = fields.Field()

    class Meta:
        model = MozillianProfile
        skip_unchanged = True
        report_skipped = True
        import_id_fields = ('mozillian_username',)
        fields = ('mozillian_username', 'email', 'application', 'full_name',)

    def dehydrate_negative_votes(self, mozillianprofile):
        return mozillianprofile.votes.filter(vote=-1).count()

    def dehydrate_skip_votes(self, mozillianprofile):
        return mozillianprofile.votes.filter(vote=0).count()

    def dehydrate_positive_votes(self, mozillianprofile):
        return mozillianprofile.votes.filter(vote=1).count()

    def dehydrate_stellar_votes(self, mozillianprofile):
        return mozillianprofile.votes.filter(vote=2).count()

    def total_votes(self, mozillianprofile):
        negatives = mozillianprofile.votes.filter(vote=-1).count()
        positives = (mozillianprofile.votes.filter(vote=1).count() +
                     mozillianprofile.votes.filter(vote=2).count())
        return (positives - negatives)

    # Import section
    def before_import(self, dataset, dry_run, **kwargs):
        """Override method for custom functionality."""

        # Normalize dataset
        if dataset.headers:
            dataset.headers = [unicode(header).lower().strip()
                               for header in dataset.headers]

    def get_or_init_instance(self, instance_loader, row):
        """Override method for custom functionality."""

        # If there isn't a username or the application is not complete,
        # do not return an instance.
        row['mozillian_username'] = get_mozillian_username(row)

        # Validate email
        email_validator = EmailValidator()
        try:
            email_validator(row['email'])
        except ValidationError:
            row['email'] = ''
        row['full_name'] = row['first_name'] + ' ' + row['last_name']

        instance, created = (super(MozillianGroupResouce, self)
                             .get_or_init_instance(instance_loader, row))
        entry_id = row['entry_id']
        application, _ = Application.objects.get_or_create(entry_id=entry_id)
        instance.application = application
        return (instance, created)

    def skip_row(self, instance, original):
        if instance and (instance.mozillian_username == '' or
                         instance.email == ''):
            return True
        return super(MozillianGroupResouce, self).skip_row(instance, original)

    def save_instance(self, instance, dry_run):
        if not dry_run:
            if not MozillianProfile.objects.filter(
                    mozillian_username=instance.mozillian_username).exists():
                super(MozillianGroupResouce, self).save_instance(instance,
                                                                 dry_run)


def update_profiles(modeladmin, request, queryset):
    update_mozillian_profiles(queryset)
update_profiles.short_description = 'Update information in Mozillian profiles.'


class MozillianProfileAdmin(ImportExportMixin, admin.ModelAdmin):
    """Mozillian profiles under /admin."""

    resource_class = MozillianGroupResouce
    model = MozillianProfile
    search_fields = ('full_name', 'country', 'mozillian_username', 'email',)
    actions = [update_profiles]
    list_display = ['mozillian_username', 'full_name', 'email', 'city',
                    'country', 'negative', 'skip', 'positive', 'stellar']

    def negative(self, obj):
        return obj.votes.filter(vote=-1).count()

    def skip(self, obj):
        return obj.votes.filter(vote=0).count()

    def positive(self, obj):
        return obj.votes.filter(vote=1).count()

    def stellar(self, obj):
        return obj.votes.filter(vote=2).count()


class VoteResource(resources.ModelResource):
    voter = fields.Field()

    class Meta:
        model = Vote
        fields = ['voter', 'nominee__full_name', 'vote']

    def dehydrate_voter(self, vote):
        return '%s %s' % (vote.voter.first_name, vote.voter.last_name)


class VoteAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = VoteResource
    model = Vote
    list_display = ['voter', 'nominee', 'vote']


class PreferredEventInline(ExportMixin, admin.TabularInline):
    resource_class = PreferredEventResource
    model = PreferredEvent


class EventInline(ExportMixin, admin.TabularInline):
    inlines = (PreferredEventInline,)
    resource_class = EventResource
    model = Application.event.through


class EventAdmin(ExportMixin, admin.ModelAdmin):
    model = Event


class MozillianGroupAdmin(ExportMixin, admin.ModelAdmin):
    model = MozillianGroup


class ApplicationAdmin(ImportExportMixin, admin.ModelAdmin):
    inlines = (EventInline,)
    resource_class = ApplicationResource
    model = Application
    search_fields = ('entry_id', 'event__name',)


admin.site.register(MozillianGroup, MozillianGroupAdmin)
admin.site.register(Vote, VoteAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(MozillianProfile, MozillianProfileAdmin)
admin.site.register(Application, ApplicationAdmin)
