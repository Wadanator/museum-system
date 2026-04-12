#!/usr/bin/env python3
"""API route for runtime actuator device states."""

from flask import Blueprint, jsonify

from ..auth import requires_auth

device_states_bp = Blueprint('device_states', __name__)


def setup_device_states_routes(dashboard):
    """Register the /api/device_states endpoint and return the blueprint."""
    controller = dashboard.controller

    @device_states_bp.route('/device_states')
    @requires_auth
    def get_device_states():
        """
        Return the runtime ON/OFF/UNKNOWN state for all tracked actuator endpoints.

        State is sourced from MQTTActuatorStateStore which aggregates desired
        states (from outgoing commands) and confirmed states (from feedback).
        Returns an empty list if the store is not yet initialised.
        """
        store = getattr(controller, 'actuator_state_store', None)
        if store is None:
            return jsonify([])
        return jsonify(store.get_all_states())

    return device_states_bp