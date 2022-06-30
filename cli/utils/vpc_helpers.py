"""Helpers to configure a VPC network on GCP."""

import textwrap

import click

from cli.utils import shared
from cli.utils.constants import GCLOUD


def _check_if_vpc_exists(stage, debug=False):
  network = stage.network
  network_project = stage.network_project
  cmd = (f'{GCLOUD} compute networks describe {network} '
         f'--verbosity critical --project={network_project}')
  status, _, _ = shared.execute_command(
      'Check if VPC already exists', cmd, report_empty_err=False, debug=debug)
  return status == 0


def _check_if_peering_exists(stage, debug=False):
  network = stage.network
  network_project = stage.network_project
  cmd = (
      f'{GCLOUD} services vpc-peerings list --network={network}'
      f' --verbosity critical --project={network_project} | grep {network}-psc')
  status, _, _ = shared.execute_command(
      'Check if VPC Peering exists', cmd, report_empty_err=False, debug=debug)
  return status == 0


def create_vpc(stage: shared.StageContext, debug: bool = False) -> None:
  """Creates a VPC in the given GCP project.

  Then allocates an IP Range for cloudSQL. finally, create peering to allow
  cloudSQL connection via private service access.

  TODO: Add support for shared VPC logic
  TODO: Manage XPN Host permissions or add pre-requisite for shared vpc

  Args:
    stage: Stage context instance.
    debug: Enables debug mode on system calls. Defaults to False.
  """
  network = stage.network
  network_project = stage.network_project

  if _check_if_vpc_exists(stage, debug=debug):
    click.echo('     VPC already exists.')
  else:
    cmd = (f'{GCLOUD} compute networks create {network}'
           f' --project={network_project} --subnet-mode=custom'
           f' --bgp-routing-mode=regional'
           f' --mtu=1460')
    shared.execute_command('Create the VPC', cmd, debug=debug)

    cmd = (f'{GCLOUD} compute addresses create {network}-psc'
           f' --global'
           f' --purpose=VPC_PEERING'
           f' --addresses=192.168.0.0'
           f' --prefix-length=16'
           f' --network={network}')
    shared.execute_command('Allocating an IP address range', cmd, debug=debug)

  if _check_if_peering_exists(stage, debug=debug):
    cmd = (f'{GCLOUD} services vpc-peerings update'
           f' --service=servicenetworking.googleapis.com'
           f' --ranges={network}-psc'
           f' --network={network}'
           f' --force'
           f' --project={network_project}')
    shared.execute_command(
        'Updating the private connection', cmd, debug=debug)
  else:
    cmd = (f'{GCLOUD} services vpc-peerings connect'
           f' --service=servicenetworking.googleapis.com'
           f' --ranges={network}-psc'
           f' --network={network}'
           f' --project={network_project}')
    shared.execute_command(
        'Creating the private connection', cmd, debug=debug)


def _check_if_connector_subnet_exists(stage, debug=False):
  """Checks that a subnet exist in the GCP project."""
  connector_subnet = stage.connector_subnet
  subnet_region = stage.subnet_region
  network_project = stage.network_project
  cmd = (f'{GCLOUD} compute networks subnets describe {connector_subnet}'
         f' --verbosity critical --project={network_project}'
         f' --region={subnet_region}')
  status, _, _ = shared.execute_command(
      'Check if VPC Subnet already exists',
      cmd,
      report_empty_err=False,
      debug=debug)
  return status == 0


def create_subnet(stage: shared.StageContext, debug: bool = False) -> None:
  """Creates a subnet in the project.

  Args:
    stage: Stage context instance.
    debug: Enables debug mode on system calls. Defaults to False.
  """
  network = stage.network
  network_project = stage.network_project
  subnet_region = stage.subnet_region
  connector_subnet = stage.connector_subnet
  connector_cidr = stage.connector_cidr

  if _check_if_connector_subnet_exists(stage, debug=debug):
    click.echo('     VPC Connector Subnet already exists.')
  else:
    cmd_connector_subnet = (
        f'{GCLOUD} compute networks subnets create {connector_subnet}'
        f' --network={network}'
        f' --range={connector_cidr}'
        f' --region={subnet_region}'
        f' --project={network_project}')

    shared.execute_command(
        'Create the VPC Connector Subnet', cmd_connector_subnet, debug=debug)


def _check_if_vpc_connector_exists(stage, debug=False):
  """Checks that a VPC connector exist in the GCP project."""
  connector: str = stage.connector
  network_project: str = stage.network_project
  subnet_region: str = stage.subnet_region
  cmd = textwrap.dedent(f"""\
      {GCLOUD} compute networks vpc-access connectors describe {connector} \\
          --region={subnet_region} \\
          --project={network_project} | grep {connector}
      """)
  status, _, _ = shared.execute_command(
      'Check if VPC Connector already exists',
      cmd,
      capture_outputs=True,
      debug=debug)
  return status == 0


def create_vpc_connector(stage: shared.StageContext,
                         debug: bool = False) -> None:
  """Creates a VPC in the project.

  TODO: Add support for shared VPC logic
  TODO: Add pre-requisite for shared vpc (XPN Host permissions)

  Args:
    stage: Stage context instance.
    debug: Enables debug mode on system calls. Defaults to False.
  """
  connector = stage.connector
  subnet_region = stage.subnet_region
  connector_subnet = stage.connector_subnet
  network_project = stage.network_project
  connector_min_instances = stage.connector_min_instances
  connector_max_instances = stage.connector_max_instances
  connector_machine_type = stage.connector_machine_type
  if _check_if_vpc_connector_exists(stage, debug=debug):
    click.echo('     VPC Connector already exists.')
  else:
    cmd = (f'{GCLOUD} compute networks vpc-access connectors create {connector}'
           f' --region {subnet_region}'
           f' --subnet {connector_subnet}'
           f' --subnet-project {network_project}'
           f' --min-instances {connector_min_instances}'
           f' --max-instances {connector_max_instances}'
           f' --machine-type {connector_machine_type}')

    shared.execute_command('Create the VPC Connector', cmd, debug=debug)
