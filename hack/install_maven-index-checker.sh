#!/usr/bin/sh -ex

# sanity check
if [[ -z "${MAVEN_INDEX_CHECKER_PATH}" ]]; then
    echo "MAVEN_INDEX_CHECKER_PATH not set"
    exit 1
fi

# download
git clone https://github.com/pkajaba/maven-index-checker.git
cd maven-index-checker
mvn clean package
mkdir --mode 775 --parents "${MAVEN_INDEX_CHECKER_PATH}"
cp target/maven-index-checker-*-jar-with-dependencies.jar "${MAVEN_INDEX_CHECKER_PATH}/maven-index-checker.jar"
mvn clean

cd "${MAVEN_INDEX_CHECKER_PATH}"
# We don't create index at build time since we've been storing it on S3
# java -jar maven-index-checker.jar
# Make sure we can later modify files in target/
mkdir --mode 777 target
