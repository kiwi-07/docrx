# pre-fetch dependencies
FROM maven:3.9.9-eclipse-temurin-21-jammy AS dependencies

ARG MAVEN_CACHE_ID

WORKDIR /opt/app
COPY service-api/pom.xml service-api/pom.xml
COPY service-core/pom.xml service-core/pom.xml
COPY service-config/pom.xml service-config/pom.xml
COPY service-device/pom.xml service-device/pom.xml
COPY service-events/pom.xml service-events/pom.xml
COPY service-firmware/pom.xml service-firmware/pom.xml
COPY service-instructions/pom.xml service-instructions/pom.xml
COPY service-media/pom.xml service-media/pom.xml
COPY service-onboarding/pom.xml service-onboarding/pom.xml
COPY service-orchestrator/pom.xml service-orchestrator/pom.xml
COPY service-gateway/pom.xml service-gateway/pom.xml
COPY service-common/pom.xml service-common/pom.xml
COPY service-uploads/pom.xml service-uploads/pom.xml
COPY service-auth/pom.xml service-auth/pom.xml
COPY service-enrichment/pom.xml service-enrichment/pom.xml
COPY service-invalid/pom.xml service-invalid/pom.xml
COPY service-deviceinfo/pom.xml service-deviceinfo/pom.xml
COPY service-vim/pom.xml service-vim/pom.xml
COPY service-notifications/pom.xml service-notifications/pom.xml
COPY service-coaching/pom.xml service-coaching/pom.xml
COPY service-ratelimit/pom.xml service-ratelimit/pom.xml
COPY pom.xml .

RUN --mount=type=cache,id=maven-cache-${MAVEN_CACHE_ID},target=/root/.m2,sharing=locked mvn -B -e org.apache.maven.plugins:maven-dependency-plugin:3.1.2:go-offline -DexcludeArtifactIds=service-core,service-events

# build the jar
FROM maven:3.9.9-eclipse-temurin-21-jammy AS builder

ARG MAVEN_CACHE_ID

WORKDIR /opt/app
#COPY --from=dependencies /root/.m2 /root/.m2
COPY --from=dependencies /opt/app/ /opt/app
COPY service-core/src /opt/app/service-core/src
COPY service-events/src /opt/app/service-events/src

RUN --mount=type=cache,id=maven-cache-${MAVEN_CACHE_ID},target=/root/.m2,sharing=locked mvn -e clean package -DskipTests

# prepare runtime env
FROM eclipse-temurin:21-jdk-jammy
LABEL maintainer="Example Team <maintainer@example.com>"
LABEL version="1.0.0"
LABEL description="Example Event Service"

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

WORKDIR /opt/app
COPY --from=builder /opt/app/service-events/target/service-events-1.0.0.jar /opt/app/service-events/service-events.jar
EXPOSE 8081

ENTRYPOINT exec java $JAVA_OPTS -jar /opt/app/service-events/service-events.jar




