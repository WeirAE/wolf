.. toctree::
   :hidden:

   sections/user_guide/index

WOLF
====

The Workflow Orchestration Layer Fabric, ``WOLF``, is a modern, open-source Python package designed to simplify the creation, management, and execution of complex workflows. It provides a flexible and scalable framework for orchestrating tasks across various environments, making it an ideal choice for scientists, engineers, and developers.

``WOLF`` uses the Python Standard Library as baseline, ensuring that it can be safely integrated into any environment without restrictions. It is designed to be extensible, allowing users to augment its capabilities with their preferred tools and libraries. 

Architecture
============
* core -- stdlib-only workflow engine, using graphlib for DAG management
* baseline -- jinja, yaml and json for configuration management and templating
* extensions -- optional dependencies for specific backends and features, e.g. ecflow, dask, etc.
* adapters -- strategy pattern implementations for various tool integrations, e.g. UWTools, WXFlow, etc

Quick Start
===========

.. code-block:: console

   wolf validate --config workflow.yaml
   wolf compile  --config workflow.yaml --backend ecflow --out ./out
   wolf inspect  --config workflow.yaml --critical-path
   wolf lint     --config workflow.yaml
   wolf capabilities

WOLF hosts its documentation on Read the Docs.
