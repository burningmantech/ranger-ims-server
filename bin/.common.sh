set -eu

wd="$(cd "$(dirname "$0")/.." && pwd)";
    mysql_image_name="mariadb:10.5.12";
mysql_container_name="ranger-ims-server_mysql";
          mysql_host="${IMS_DB_HOST_NAME:-host.docker.internal}";
      mysql_database="${IMS_DB_DATABASE:-ims}";
          mysql_user="${IMS_DB_USER_NAME:-ims}";
      mysql_password="${IMS_DB_PASSWORD:-donothing}";

image_repo="ranger-ims-server";
 image_tag="dev";
image_name="${image_repo}:${image_tag}";

build_image_name="${image_repo}_build";
  ims_image_name="${image_name}";

container_name="ranger-ims-server";


mysql_port () {
    local mapping="$(docker port "${mysql_container_name}")";
    local netloc="${mapping##* -> }";
    local port="${netloc##*:}";

    echo "${port}";
}
