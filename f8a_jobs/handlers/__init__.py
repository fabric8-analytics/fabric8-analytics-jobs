"""Module containing all handlers supported by the job service."""

from .aggregate_crowd_source_tags import AggregateCrowdSourceTags
from .aggregate_github_manifest_pkgs import AggregateGitHubManifestPackages
from .aggregate_topics import AggregateTopics
from .book_keeping import BookKeeping
from .clean_postgres import CleanPostgres
from .error import ErrorHandler
from .flow import FlowScheduling
from .github_most_starred import GitHubMostStarred
from .github_manifests import GitHubManifests
from .golang_popular_analyses import GolangPopularAnalyses
from .kronos_data_update import KronosDataUpdater
from .maven_popular_analyses import MavenPopularAnalyses
from .maven_releases import MavenReleasesAnalyses
from .npm_popular_analyses import NpmPopularAnalyses
from .nuget_popular_analyses import NugetPopularAnalyses
from .python_popular_analyses import PythonPopularAnalyses
from .selective_flow import SelectiveFlowScheduling
from .sync_to_graph import SyncToGraph
from .invoke_graph_sync import InvokeGraphSync

# make code checkers happy
assert AggregateCrowdSourceTags is not None
assert AggregateGitHubManifestPackages is not None
assert AggregateTopics is not None
assert BookKeeping is not None
assert CleanPostgres is not None
assert ErrorHandler is not None
assert FlowScheduling is not None
assert GitHubMostStarred is not None
assert GitHubManifests is not None
assert GolangPopularAnalyses is not None
assert KronosDataUpdater is not None
assert MavenPopularAnalyses is not None
assert MavenReleasesAnalyses is not None
assert NpmPopularAnalyses is not None
assert NugetPopularAnalyses is not None
assert PythonPopularAnalyses is not None
assert SelectiveFlowScheduling is not None
assert SyncToGraph is not None
assert InvokeGraphSync is not None
