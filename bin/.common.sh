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


# State
host_ims_port="$("${wd}/bin/find_port")";
 db_container_name="";
ims_container_name="";


##
# DB Container
##

start_db_container() {
    trap cleanup_db_container EXIT;

    db_container_name="${IMS_DB_CONTAINER_NAME:-ranger-ims-db-tests_${$}}";

    echo "Starting database container: ${db_container_name}...";

    docker run                                    \
        --rm --detach                             \
        --name="${db_container_name}"             \
        --env="MYSQL_RANDOM_ROOT_PASSWORD=yes"    \
        --env="MYSQL_DATABASE=${mysql_database}"  \
        --env="MYSQL_USER=${mysql_user}"          \
        --env="MYSQL_PASSWORD=${mysql_password}"  \
        --env="MYSQL_ROOT_HOST=%"                 \
        "${mysql_image_name}"                     \
        > /dev/null;
}


wait_for_db() {
    started() {
        docker logs "${db_container_name}" 2>&1 \
            | grep -e 'mysqld (mysqld .*) starting as process 1 ' \
            ;
    }

    while true; do
        printf "Waiting on database to start... ";

        if [ -n "$(started)" ]; then
            echo "Database started.";
            break;
        fi;
        sleep 1;
        echo "";
    done;
}


db_sql() {
    docker exec --interactive "${db_container_name}"               \
        mysql                                                      \
            --user="${mysql_user}" --password="${mysql_password}"  \
            --database="${mysql_database}"                         \
            "$@"                                                   \
            ;
}


db_init() {
    if [ -n "${RANGER_CLUBHOUSE_TEST_DB_DUMP:-}" ]; then
        echo "Importing test Clubhouse database dump...";
        gunzip < "${RANGER_IMS_TEST_DB_DUMP}" | db_sql;
    fi;
    if [ -n "${RANGER_IMS_TEST_DB_DUMP:-}" ]; then
        echo "Importing test IMS database dump...";
        gunzip < "${RANGER_IMS_TEST_DB_DUMP}" | db_sql;
    fi;
}


cleanup_db_container() {
    if [ -n "${db_container_name}" ]; then
        echo "Terminating database container: ${db_container_name}...";

        docker kill "${db_container_name}" > /dev/null;

        db_container_name="";
    fi;
}


mysql_port () {
    local mapping="$(docker port "${mysql_container_name}")";
    local netloc="${mapping##* -> }";
    local port="${netloc##*:}";

    echo "${port}";
}


##
# IMS Container
##

start_ims_container() {
    ims_container_name="ranger-ims-test_${$}";

    trap cleanup_ims_container EXIT;

    echo "Starting IMS application container: ${ims_container_name}...";

    docker run                                         \
        --rm --detach                                  \
        --name="${ims_container_name}"                 \
        --env="IMS_DB_HOST_NAME=${db_container_name}"  \
        --env="IMS_DB_DATABASE=${mysql_database}"      \
        --env="IMS_DB_USER_NAME=${mysql_user}"         \
        --env="IMS_DB_PASSWORD=${mysql_password}"      \
        --link="${db_container_name}"                  \
        --publish="${host_ims_port}:80"                \
        "${ims_image_name}"                            \
        > /dev/null;
}


wait_for_ims() {
    local response="$(mktemp)";
    local    error="$(mktemp)";

    local count=0;
    local e;

    check_timeout() {
        local timeout=60;

        if [ ${count} -gt ${timeout} ]; then
            echo "ERROR: Timed out";
            echo "Logs:";
            docker logs "${ims_container_name}";
            return 1;
        fi;
    }

    while true; do
        printf "Waiting on IMS application to start... ";

        http_get "${host_ims_port}" / > "${response}" 2> "${error}" \
            && e=0 || e=$?;

        count=$((${count} + 1));

        check_timeout || return 1;

        if [ ${e} -eq 7 ]; then
            echo "Connection refused from server. ";
            sleep 1;
            continue;
        fi;

        if [ ${e} -eq 52 ]; then
            echo "Empty reply from server. ";
            sleep 1;
            continue;
        fi;

        if [ ${e} -eq 56 ]; then
            echo "Connection to server reset. ";
            sleep 1;
            continue;
        fi;

        if [ ${e} -ne 0 ]; then
            fail "Error HTTP status from server.";
            echo "Error from curl:"; cat "${error}";
            echo "Response:"; cat "${response}";
            return 1;
        fi;

        echo "IMS application is responding.";
        break;
    done;

    rm "${response}" "${error}";
}


cleanup_ims_container() {
    if [ -n "${ims_container_name}" ]; then
        echo "Terminating IMS application container: ${ims_container_name}...";

        docker kill "${ims_container_name}" > /dev/null;

        ims_container_name="";
    fi;

    cleanup_db_container;
}
