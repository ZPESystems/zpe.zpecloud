# Ansible Collection - zpe.zpecloud

Documentation for the collection.

# How to install

- git clone https://github.com/ZPESystems/zpe.zpecloud.git
- cd zpe.cloud
- ansible-galaxy collection build
- ansible-galaxy collection install zpe-zpecloud-1.0.0.tar.gz

Note: If you want to reinstall the collection, it is necessary to remove it first
- rm -rf /etc/ansible/collections/ansible_collections/zpe/


# How to test

- Install docker
- Install ansible-core
- Install collection
- Run ansible-test sanity --docker
- Run ansible-test units --docker