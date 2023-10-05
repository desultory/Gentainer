# Gentainer

Prepares and builds Gentoo based LXC containers

## Modules

Modules contain code for specific tasks.
If `parameters` is defined in an imported module, it will be added to the `ContainerConfig` class.
Validation functions can be defined using the name `validate_{parameter}` for any registered parameter.

### Users

The Users module is used to create an unprivileged user for a container, and configure its usernets.

The `username` parameter should be configured in container configs, and defines the username associated with this container.
The `lxc_usernet_file` should be set globally, or defaults to `/etc/lxc/lxc-usernet`.
The `usernet_allocation` dict should be configured for each container, and is a dict where the key is the interface name, and value is the allocation count.

### Layers

Used to define how image layers are created.

The `dir_back` defines the backing type for layers, currently only `btrfs` is implemented.
The `base_image` parameter is optional and defines the base image for the layer to be created on.
This will define the subvolume source when creating btrfs snapshots.

### Builder

The Builder targets a `build_dir` which should be created with `Layers`, then emerges the defined `packages` into it.

Packages defined in the `package` parameter are validated using the system package db.
