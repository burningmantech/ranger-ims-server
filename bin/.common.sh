set -eu

wd="$(cd "$(dirname "$0")/.." && pwd)";

image_repo="ranger-ims-server";
 image_tag="dev";
image_name="${image_repo}:${image_tag}";

build_image_name="${image_repo}_build";
  ims_image_name="${image_name}";

container_name="ranger-ims-server";
