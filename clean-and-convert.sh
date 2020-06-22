#!/usr/bin/env bash
set -e

if [[ -z "$2" ]]; then
    echo "Usage: clean-and-convert.sh <INPUT_DIR> <OUTPUT_DIR>"
    exit 1
fi

input_dir="$(realpath "$1")"
export output_dir="$(realpath "$2")"
num_jobs=10

mkdir -p "${output_dir}"

function clean_convert {
    in_path="$1"
    wav_name="$(basename "${in_path}")"
    temp_path="${output_dir}/_${wav_name}"
    out_path="${output_dir}/${wav_name}"
    sox --ignore-length "${in_path}" "${temp_path}"
    sox "${temp_path}" "${out_path}" trim 0.25 -0.3 pad 0.25 0.3
    rm -f "${temp_path}"
}

export -f clean_convert

find "${input_dir}" -type f -name '*.wav' -print0 | \
    parallel -0 -n 1 -j "${num_jobs}" clean_convert
