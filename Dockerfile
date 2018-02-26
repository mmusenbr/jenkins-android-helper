FROM openjdk:8-jdk
MAINTAINER Michael Musenbrock

RUN apt-get update && apt-get install -y --no-install-recommends \
		wget \
		lsof \
		unzip \
		uuid \
	&& rm -rf /var/lib/apt/lists/*
RUN wget "https://github.com/redeamer/jenkins-android-helper/releases/download/0.1.01/jenkins-android-helper_0.1.01_all.deb"
RUN dpkg -i jenkins-android-helper_0.1.01_all.deb
