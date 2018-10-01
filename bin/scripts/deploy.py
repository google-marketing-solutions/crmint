import click
import os, os.path
from appcli import CRMintCLI
import constants

stage_file = ""

def _file_stage_exists(stage):
    global stage_file
    stage_file = "{}/{}.sh".format(constants.STAGE_DIR, stage)
    print(stage_file)
    return os.path.isfile(stage_file)

@click.group()
def cli():
    """Entry point to CRMint command line interface"""
    pass

@cli.command('cron')
@click.argument('stage')
@click.option('--cron-frequency-minutes', '-cm', default=None, show_default=True,
                help='Cron job schedule in minutes')
@click.option('--cron-frequency-hours', '-ch', default=None, show_default=True,
                help='Cron job schedule in hours')
def cron(stage, cron_frequency_minutes, cron_frequency_hours):
    global stage_file
    if not _file_stage_exists(stage):
        click.echo("Stage file not found.")
        exit(1)
    else:
        with open(constants.CRON_FILE, "w") as cron_file:
            if cron_frequency_minutes and cron_frequency_hours:
                cron_file.write("")
            else:
                if cron_frequency_minutes:
                    cron_file.write(constants.CRON_TEMPLATE
                        .format(str(cron_frequency_minutes), "minutes"))
                if cron_frequency_hours:
                    cron_file.write(cconstants.CRON_TEMPLATE
                        .format(str(cron_frequency_minutes), "hours"))
        os.system("""source \"{}\"
                source \"{}/deploy/before_hook.sh\"
                source \"{}/deploy/cron.sh\"""".format(stage_file,
                    constants.SCRIPTS_DIR,
                    constants.SCRIPTS_DIR
                ))

if __name__ == '__main__':
    cli()