############################################################################
# To use this code with Tripleo, the container must be modified as follows #
# Please edit the release and tag variables to match your enviroment       #
# See http://tripleo.org/install/containers_deployment/3rd_party.html      #
############################################################################
FROM $LISTENING_IP_ADDRESS:8787/tripleo$RELEASE/centos-binary-cinder-volume:$CONTAINERTAG

# switch to root and install a custom RPM, etc.
USER root
RUN git clone --depth=1 https://github.com/iXsystems/cinder /tmp/cinder
RUN cp -R /tmp/cinder/driver/ixsystems /usr/lib/python2.7/site-packages/cinder/volume/drivers/ 

# switch the container back to the default user
USER cinder
