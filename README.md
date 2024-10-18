# ZPE Cloud Ansible Collection

This Ansible collection includes content to help automate the management of Nodegrid appliances via ZPE Cloud.

## Installation

### Install via Ansible Galaxy

This collection can be installed with Ansible Galaxy command-line tool:

```
ansible-galaxy collection install zpe.zpecloud
```

### Install from source code

```
git clone https://github.com/ZPESystems/zpe.zpecloud.git
cd zpe.zpecloud/
ansible-galaxy collection build
ansible-galaxy collection install zpe-zpecloud-<version>.tar.gz
```

Note: If you want to reinstall the collection, it is necessary to remove it first.

```
rm -rf /etc/ansible/collections/ansible_collections/zpe/zpecloud/
```

## Testing

- Install docker
- Install ansible-core
- Install collection

```
cd /etc/ansible/collections/ansible_collections/zpe/zpecloud
ansible-test sanity --docker --requirements requests
ansible-test units --docker
```
