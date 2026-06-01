Installation
============

Install using a Unifiied Spack Environment
------------------------------------------

To install ``WOLF`` using a unified Spack environment on a NOAA RDHPCS tier 1 platform:

#. Identify the current environment by running the following command:

   .. code-block:: bash

      spack env active

#. Install the ``WOLF`` module by running the following command:

   .. code-block:: bash

      module load wolf

Create a Standalone Spack Environment
-------------------------------------

To install ``WOLF`` using a standalone Spack environment:

#. Clone spack-stack locally from GitHub:

    .. code-block:: bash
    
        git clone -b https://github.com/JCSDA/spack-stack

# Create a spack environment for ``WOLF``

    .. code-block:: bash

        spack env create -d wolf

# Add ``WOLF`` to the environment

    .. code-block:: bash

        spack env add wolf

Build ``WOLF`` Locally
----------------------

To build ``WOLF`` locally::

#. Clone ``WOLF`` locally from GitHub:

    .. code-block:: bash
    
        git clone -b https://github.com/WeirAE/wolf

#. Build ``WOLF`` using the provided Makefile:

    .. code-block:: bash

        cd wolf
        make -j 4
