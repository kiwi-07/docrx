# pre-fetch dependencies
FROM maven:3.9.9-eclipse-temurin-21-jammy AS dependencies

ARG MAVEN_CACHE_ID

WORKDIR /opt/akt
COPY aether-command-service/pom.xml aether-command-service/pom.xml
COPY aether-commons/pom.xml aether-commons/pom.xml
COPY aether-configota-service/pom.xml aether-configota-service/pom.xml
COPY aether-device-client/pom.xml aether-device-client/pom.xml
COPY aether-event-service/pom.xml aether-event-service/pom.xml
COPY aether-firmwareota-service/pom.xml aether-firmwareota-service/pom.xml
COPY aether-instructionota-service/pom.xml aether-instructionota-service/pom.xml
COPY aether-media-service/pom.xml aether-media-service/pom.xml
COPY aether-onboarding-service/pom.xml aether-onboarding-service/pom.xml
COPY aether-orchestrator/pom.xml aether-orchestrator/pom.xml
COPY aether-api-service/pom.xml aether-api-service/pom.xml
COPY aether-api-commons/pom.xml aether-api-commons/pom.xml
COPY aether-fileuploadota-service/pom.xml aether-fileuploadota-service/pom.xml
COPY aether-auth-core/pom.xml aether-auth-core/pom.xml
COPY aether-eventenrichment-service/pom.xml aether-eventenrichment-service/pom.xml
COPY aether-invalidrequest-service/pom.xml aether-invalidrequest-service/pom.xml
COPY aether-deviceinfo-service/pom.xml aether-deviceinfo-service/pom.xml
COPY aether-vimota-service/pom.xml aether-vimota-service/pom.xml
COPY aether-notification-service/pom.xml aether-notification-service/pom.xml
COPY aether-eoddrivercoaching-service/pom.xml aether-eoddrivercoaching-service/pom.xml
COPY aether-rate-limit-core/pom.xml aether-rate-limit-core/pom.xml
COPY pom.xml .

RUN --mount=type=cache,id=maven-cache-${MAVEN_CACHE_ID},target=/root/.m2,sharing=locked mvn -B -e org.apache.maven.plugins:maven-dependency-plugin:3.1.2:go-offline -DexcludeArtifactIds=aether-commons,aether-event-service

# build the jar
FROM maven:3.9.9-eclipse-temurin-21-jammy AS builder

ARG MAVEN_CACHE_ID

WORKDIR /opt/akt
#COPY --from=dependencies /root/.m2 /root/.m2
COPY --from=dependencies /opt/akt/ /opt/akt
COPY aether-commons/src /opt/akt/aether-commons/src
COPY aether-event-service/src /opt/akt/aether-event-service/src

RUN --mount=type=cache,id=maven-cache-${MAVEN_CACHE_ID},target=/root/.m2,sharing=locked mvn -e clean package -DskipTests

# prepare runtime env
FROM eclipse-temurin:21-jdk-jammy
LABEL maintainer="Platform Engineering <platform_engineering@akteena.com>"
LABEL version="2.22.0-SNAPSHOT"
LABEL description="Aether Event Service"

# Install essential networking tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    iputils-ping \
    telnet \
    curl \
    wget \
    traceroute \
    netcat \
    net-tools \
    iproute2 \
    dnsutils \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/akt
COPY --from=builder /opt/akt/aether-event-service/target/aether-event-service-2.22.0-SNAPSHOT.jar /opt/akt/aether-event-service/aether-event-service.jar
EXPOSE 8081

ENTRYPOINT exec java $JAVA_OPTS -jar /opt/akt/aether-event-service/aether-event-service.jar




