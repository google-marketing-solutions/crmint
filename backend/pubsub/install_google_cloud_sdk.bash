#! /bin/bash

# curl https://dl.google.com/dl/cloudsdk/release/install_google_cloud_sdk.bash | bash

__SDK_DIR=google-cloud-sdk
__SDK_URL_DIR=https://dl.google.com/dl/cloudsdk/channels/rapid
__SDK_TGZ=google-cloud-sdk.tar.gz
__SDK_TTY=/dev/tty

COMMAND=${0##*/}

usage() {
  echo "
$COMMAND [ --disable-prompts ] [ --install-dir=DIRECTORY ]

Installs the Google Cloud SDK by downloading and unpacking
$__SDK_TGZ in a directory of your choosing, and then runs the
install.sh script included in the download.

--disable-prompts
  Disables prompts. Prompts are always disabled when there is no controlling
  tty. Alternatively export CLOUDSDK_CORE_DISABLE_PROMPTS=1 before running
  the script.

--install-dir=DIRECTORY
  Sets the installation root directory to DIRECTORY. The Cloud SDK will be
  installed in DIRECTORY/$__SDK_DIR. The default is \$HOME. Alternatively,
  export CLOUDSDK_INSTALL_DIR=DIRECTORY before running the script or
  export PREFIX=DIRECTORY for backwards compatibility with older versions of
  this script.
" >&2
  exit 2
}

# Accept PREFIX as a CLOUDSDK_INSTALL_DIR default for backwards compatibility.
if [ -z "$CLOUDSDK_INSTALL_DIR" ]; then
  CLOUDSDK_INSTALL_DIR=$PREFIX
fi

while true; do
  case $# in
    0)  break ;;
  esac
  case $1 in
    --disable-prompts)
      CLOUDSDK_CORE_DISABLE_PROMPTS=1
      export CLOUDSDK_CORE_DISABLE_PROMPTS
      ;;
    --install-dir|--prefix)
      shift
      case $# in
        0)
          echo "$COMMAND: --install-dir: DIRECTORY argument expected." >&2
          exit 1
          ;;
      esac
      CLOUDSDK_INSTALL_DIR=$1
      ;;
    --install-dir=*|--prefix=*)
      CLOUDSDK_INSTALL_DIR=${1#*=}
      ;;
    --TEST-MOCK-SCRIPT)  # Undocumented test mock script.
      shift
      case $# in
        0)
          echo "$COMMAND: --TEST-MOCK-SCRIPT: SCRIPT argument expected." >&2
          exit 1
          ;;
      esac
      . "$1" || exit
      ;;
    --TEST-MOCK-SCRIPT=*)  # Undocumented test mock script.
      . "${1#*=}" || exit
      ;;
    *)
      usage
      ;;
  esac
  shift
done

download_src=$__SDK_URL_DIR/$__SDK_TGZ

# Prompt the user for some string input, with a default. If the user enters
# nothing, use the default. Put the result in the target variable.
promptWithDefault() {
  # $1: The question being asked.
  # $2: The default answer.
  # $3: The name of the variable to put the result in.
  if [ -n "$CLOUDSDK_CORE_DISABLE_PROMPTS" ]; then
    __pwd_response=""
  else
    __pwd_message="$1 ($2): "
    read -p "$__pwd_message" __pwd_response
  fi
  if [ -z "$__pwd_response" ]; then
    __pwd_response=$2
  fi
  # Expand embedded $... and leading ~... but do not glob.
  set -o noglob
  __pwd_variable=$3
  eval set -- $__pwd_response
  eval $__pwd_variable="'$*'"
  set +o noglob
}

# Ask the user a yes-or-no question, and get put "1" or nothing in the target
# variable, so it can be tested in an if statement.
promptYesNo() {
  # $1: The question being asked.
  # $2: The default answer, 'y' or 'n'.
  # $3: The name of the variable to put "1" or nothing in.
  if [ -n "$CLOUDSDK_CORE_DISABLE_PROMPTS" ]; then
    __pyn_response=""
  else
    __pyn_default="y/N"
    if [ "$2" == "y" ]; then
      __pyn_default="Y/n"
    fi
    __pyn_message="$1 ($__pyn_default): "
    read -p "$__pyn_message" __pyn_response
  fi
  if [ -z "$__pyn_response" ]; then
    __pyn_response=$2
  fi
  if [ "$__pyn_response" == "y" -o "$__pyn_response" == "Y" ]; then
    eval $3=1
  else
    eval $3=
  fi
}

trace() {
  echo "$@" >&2
  "$@"
}

download() {
  # $1: The source URL.
  # $2: The local file to write to.
  __download_src=$1
  __download_dst=$2
  if trace which curl >/dev/null; then
    trace curl -# -f "$__download_src" > "$__download_dst"
  elif trace which wget >/dev/null; then
    trace wget -O - "$__download_src" > "$__download_dst"
  else
    echo "Either curl or wget must be installed to download files." >&2
    return 1
  fi
}

install() {
  if [ -z "$CLOUDSDK_INSTALL_DIR" ]; then
    CLOUDSDK_INSTALL_DIR=$HOME
  fi
  install_dir=$CLOUDSDK_INSTALL_DIR
  download_dst=$scratch/$__SDK_TGZ

  # Download the bundle from Google.
  download "$download_src" "$download_dst" || return
  echo

  __install_msg="Installation directory (this will create a $__SDK_DIR subdirectory)"
  while true; do
    promptWithDefault "$__install_msg" "$install_dir" install_dir
    if [ -z "$install_dir" ]; then
      if [ -n "$CLOUDSDK_CORE_DISABLE_PROMPTS" ]; then
        echo "Specify an installation directory, either by --install-dir=... or export CLOUDSDK_INSTALL_DIR=..." >&2
        return 1
      fi
      continue
    fi
    trace mkdir -p "$install_dir" || return

    # Make sure the destination is clear.
    destination="$install_dir/$__SDK_DIR"
    if [ ! -e "$destination" ]; then
      break
    fi
    echo "\"$destination\" already exists and may contain out of date files." >&2
    promptYesNo "Remove it before installing?" n REMOVE_OLD
    if [ -n "$REMOVE_OLD" ]; then
      trace rm -rf "$destination"
      if [ ! -e "$destination" ]; then
        break
      fi
      echo "Failed to remove $destination." >&2
      __install_msg="Installation directory (choose the default to try the remove again)"
    elif [ -n "$CLOUDSDK_CORE_DISABLE_PROMPTS" ]; then
      echo "Remove $destination or select a new installation directory, then run again." >&2
      return 1
    fi
  done

  # Extract the bundle to the destination.
  trace tar -C "$install_dir" -zxvf "$download_dst" || return
  echo

  # Run the bundled install script.
  trace "$destination/install.sh" || return
}

PS4=
scratch=$(mktemp -d -t tmp.XXXXXXXXXX) && trap "command rm -rf $scratch" EXIT || exit 1
if [ -z "$CLOUDSDK_CORE_DISABLE_PROMPTS" ]; then
  if { command true < $__SDK_TTY; } > /dev/null 2>&1; then
    # Grab prompt input from the tty.
    install < $__SDK_TTY
  else
    # No tty so don't prompt.
    CLOUDSDK_CORE_DISABLE_PROMPTS=1
    export CLOUDSDK_CORE_DISABLE_PROMPTS
    install
  fi
else
  install
fi
