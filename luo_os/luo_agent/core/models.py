#!/usr/bin/env python3
"""LUOKAI Model Manager — LUOKAI is the only model needed."""

LUOKAI_MODEL = "luokai-1.0"

class ModelManager:
    def __init__(self, luokai_url="http://localhost:3000"):
        self.luokai_url = luokai_url

    def get_available_models(self):
        return [{"name": LUOKAI_MODEL, "type": "native"}]

    def is_model_available(self, name):
        return True

    def get_model_info(self, name):
        return {"name": LUOKAI_MODEL, "type": "native", "description": "LUOKAI native inference"}

def create_model_manager(luokai_url="http://localhost:3000"):
    return ModelManager(luokai_url)

def get_best_available_model(luokai_url="http://localhost:3000"):
    return LUOKAI_MODEL

def get_fast_model(luokai_url="http://localhost:3000"):
    return LUOKAI_MODEL
