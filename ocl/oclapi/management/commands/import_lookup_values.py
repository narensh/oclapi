import sys

import haystack
from django.contrib.auth.models import User
from django.core.management import BaseCommand
from django.core.management.base import OutputWrapper
from haystack.management.commands import update_index

from concepts.importer import ConceptsImporter
from oclapi.management.commands import ImportActionHelper
from oclapi.models import ConceptContainerVersionModel
from orgs.models import Organization
from sources.models import Source, SourceVersion
from collection.models import Collection, CollectionVersion


class Command(BaseCommand):
    help = 'import lookup values'

    def handle(self, *args, **options):
        self.clear_all_processing()

        user = User.objects.filter(username='root').get()

        org = self.create_organization(user)

        sources = self.create_sources(org, user)

        importer_confs = [
            {'source': sources['Classes'], 'file': "./concept_classes.json"},
            {'source': sources['Locales'], 'file': "./locales.json"},
            {'source': sources['Datatypes'], 'file': "./datatypes_fixed.json"},
            {'source': sources['NameTypes'], 'file': "./nametypes_fixed.json"},
            {'source': sources['DescriptionTypes'], 'file': "./description_types.json"},
            {'source': sources['MapTypes'], 'file': "./maptypes_fixed.json"}
        ]

        SourceVersion.migrate_concepts_and_mappings_field()

        for conf in importer_confs:
            file = open(conf['file'], 'rb')
            source = conf['source']

            importer = ConceptsImporter(source, file, user, OutputWrapper(sys.stdout), OutputWrapper(sys.stderr), save_validation_errors=False)
            importer.import_concepts(**options)

    def create_organization(self, user):
        org = None
        if Organization.objects.filter(mnemonic='OCL').count() < 1:
            org = Organization(mnemonic='OCL', name='Open Concept Lab', company="Open Concept Lab", members=[user.id],
                               created_by='root', updated_by='root')
            org.full_clean()
            org.save()
        else:
            org = Organization.objects.get(mnemonic='OCL')
        return org

    def create_sources(self, org, user):
        sources = dict()

        kwargs = {
            'parent_resource': org
        }

        for source_name in ['Locales', 'Classes', 'Datatypes', 'DescriptionTypes', 'NameTypes', 'MapTypes']:
            source = None

            if Source.objects.filter(parent_id=org.id, mnemonic=source_name).count() < 1:
                source = Source(name=source_name, mnemonic=source_name, full_name=source_name, parent=org,
                                created_by=user, default_locale='en', supported_locales=['en'], updated_by=user)
                Source.persist_new(source, user, **kwargs)
            else:
                source = Source.objects.get(parent_id=org.id, mnemonic=source_name)
            sources[source_name] = source


        return sources

    def clear_all_processing(self):
        ConceptContainerVersionModel.clear_all_processing(SourceVersion)
        ConceptContainerVersionModel.clear_all_processing(CollectionVersion)
