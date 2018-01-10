#!/usr/bin/env python3

"""Module containing all handlers supported by the job service."""

from .aggregate_crowd_source_tags import AggregateCrowdSourceTags
from .clean_postgres import CleanPostgres
from .error import ErrorHandler
from .flow import FlowScheduling
from .maven_popular_analyses import MavenPopularAnalyses
from .npm_popular_analyses import NpmPopularAnalyses
from .nuget_popular_analyses import NugetPopularAnalyses
from .python_popular_analyses import PythonPopularAnalyses
from .golang_popular_analyses import GolangPopularAnalyses
from .selective_flow import SelectiveFlowScheduling
from .sync_to_graph import SyncToGraph
from .aggregate_topics import AggregateTopics
from .github_most_starred import GitHubMostStarred
from .github_manifests import GitHubManifests
from .aggregate_github_manifest_pkgs import AggregateGitHubManifestPackages
from .maven_releases import MavenReleasesAnalyses
from .kronos_data_update import KronosDataUpdater
