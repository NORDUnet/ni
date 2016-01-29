# -*- coding: utf-8 -*-

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.shortcuts import render, get_object_or_404
from ..models import NodeHandle
import json

from apps.noclook import forms

class ImportNodesView(View):
    def get(self, request, slug, handle_id):
        parent = get_object_or_404(NodeHandle, handle_id=handle_id)
        return render(request, 'noclook/import/upload.html')
    def post(self, request, slug, handle_id):
        parent = get_object_or_404(NodeHandle, handle_id=handle_id)
        if request.FILES['file']:
            data = json.load(request.FILES['file'])
        return render(request, 'noclook/import/edit.html', {'parent': parent, 'data': data})
    
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ImportNodesView, self).dispatch(*args, **kwargs)
    # TODO: based on slug decide allowed node types

