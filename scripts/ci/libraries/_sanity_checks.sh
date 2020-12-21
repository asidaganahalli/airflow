#!/usr/bin/env bash
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

# Fixes a file that is expected to be a file. If - for whatever reason - the local file is not created
# When mounting it to container, docker assumes it is a missing directory and creates it. Such mistakenly
# Created directories should be removed and replaced with files
function sanity_checks::sanitize_file() {
    if [[ -d "${1}" ]]; then
        rm -rf "${1}"
    fi
    touch "${1}"
}

# Those files are mounted into container when run locally
# .bash_history is preserved and you can modify .bash_aliases and .inputrc
# according to your liking
function sanity_checks::sanitize_mounted_files() {
    sanity_checks::sanitize_file "${AIRFLOW_SOURCES}/.bash_history"
    sanity_checks::sanitize_file "${AIRFLOW_SOURCES}/.bash_aliases"
    sanity_checks::sanitize_file "${AIRFLOW_SOURCES}/.inputrc"

    # When KinD cluster is created, the folder keeps authentication information
    # across sessions
    mkdir -p "${AIRFLOW_SOURCES}/.kube" >/dev/null 2>&1
}

#
# Creates cache directory where we will keep temporary files needed for the docker build
#
# This directory will be automatically deleted when the script is killed or exists (via trap)
# Unless SKIP_CACHE_DELETION variable is set. You can set this variable and then see
# the output/files generated by the scripts in this directory.
#
# Most useful is out.log file in this directory storing verbose output of the scripts.
#
#
# Checks if core utils required in the host system are installed and explain what needs to be done if not
#
function sanity_checks::check_if_coreutils_installed() {
    set +e
    getopt -T >/dev/null
    GETOPT_RETVAL=$?

    if [[ $(uname -s) == 'Darwin' ]] ; then
        command -v gstat >/dev/null
        STAT_PRESENT=$?
    else
        command -v stat >/dev/null
        STAT_PRESENT=$?
    fi

    command -v md5sum >/dev/null
    MD5SUM_PRESENT=$?

    set -e

    CMDNAME="$(basename -- "$0")"
    export CMDNAME
    readonly CMDNAME

    ####################  Parsing options/arguments
    if [[ ${GETOPT_RETVAL} != 4 || "${STAT_PRESENT}" != "0" || "${MD5SUM_PRESENT}" != "0" ]]; then
        verbosity::print_info
        if [[ $(uname -s) == 'Darwin' ]] ; then
            echo """
${COLOR_RED_ERROR} You are running ${CMDNAME} in OSX environment and ou need to install gnu commands

Run 'brew install gnu-getopt coreutils'

Then link the gnu-getopt to become default as suggested by brew.

If you use bash, you should run these commands:

echo 'export PATH=\"/usr/local/opt/gnu-getopt/bin:\$PATH\"' >> ~/.bash_profile
. ~/.bash_profile

If you use zsh, you should run these commands:

echo 'export PATH=\"/usr/local/opt/gnu-getopt/bin:\$PATH\"' >> ~/.zprofile
. ~/.zprofile

Either source the profile file as shown above, or re-login afterwards.

After that, your PATH variable should start with \"/usr/local/opt/gnu-getopt/bin\"
Your current path is ${PATH}
${COLOR_RESET}
"""
        else
            echo """
${COLOR_RED_ERROR} You do not have necessary tools in your path (getopt, stat, md5sum).
Please install latest/GNU version of getopt and coreutils.
This can usually be done with 'apt install util-linux coreutils'
${COLOR_RESET}
"""
        fi
        verbosity::print_info
        exit 1
    fi
}

#
# Asserts that we are not inside of the container
#
function sanity_checks::assert_not_in_container() {
    if [[ ${SKIP_IN_CONTAINER_CHECK:=} == "true" ]]; then
        return
    fi
    if [[ -f /.dockerenv ]]; then
        echo """
\e[31mERROR: You are inside the Airflow docker container

You should only run this script from the host.
Learn more about how we develop and test airflow at:
https://github.com/apache/airflow/blob/master/TESTING.rst

"""
        exit 1
    fi
}

# Changes directory to local sources
function sanity_checks::go_to_airflow_sources {
    verbosity::print_info
    pushd "${AIRFLOW_SOURCES}" &>/dev/null || exit 1
    verbosity::print_info
    verbosity::print_info "Running in host in $(pwd)"
    verbosity::print_info
}

#
# Performs basic sanity checks common for most of the scripts in this directory
#
function sanity_checks::basic_sanity_checks() {
    sanity_checks::assert_not_in_container
    initialization::set_default_python_version_if_empty
    sanity_checks::go_to_airflow_sources
    sanity_checks::check_if_coreutils_installed
    sanity_checks::sanitize_mounted_files
}
