import os
import uuid
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views import View
from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image
import json

from .forms import ImageUploadForm
from .models import HairTransformation, TransformationResult
from .utils.hair_ai import DjangoHairTransformation
import threading

class HomeView(View):
    def get(self, request):
        form = ImageUploadForm()
        return render(request, 'hair_transformation/home.html', {'form': form})
    
    def post(self, request):
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the uploaded image
            hair_transformation = form.save(commit=False)
            hair_transformation.session_id = str(uuid.uuid4())
            hair_transformation.save()
            
            # Process the image
            return redirect('processing_view', session_id=hair_transformation.session_id)
        
        return render(request, 'hair_transformation/home.html', {'form': form})

class ProcessingView(View):
    def get(self, request, session_id):
        try:
            hair_transformation = HairTransformation.objects.get(session_id=session_id)

            # If results already exist, go to results page
            if hair_transformation.results.exists():
                return redirect('results_view', session_id=session_id)

            # Use a simple lock file in MEDIA_ROOT/processing to avoid starting multiple background tasks
            processing_dir = os.path.join(settings.MEDIA_ROOT, 'processing')
            os.makedirs(processing_dir, exist_ok=True)
            lock_path = os.path.join(processing_dir, f"{session_id}.lock")

            def background_process(session_id_local):
                try:
                    processor = DjangoHairTransformation()
                    image_path = hair_transformation.original_image.path
                    results = processor.process_image(image_path, session_id_local)

                    if results:
                        # Save analysis data
                        hair_transformation.skin_tone = results['analysis_data']['skin_tone']
                        hair_transformation.ethnicity = results['analysis_data']['ethnicity']
                        hair_transformation.face_shape = results['analysis_data']['face_shape']
                        hair_transformation.hair_length = results['analysis_data']['hair_length']
                        hair_transformation.hair_texture = results['analysis_data']['hair_texture']
                        hair_transformation.style_recommendations = results['recommendations']['styles']
                        hair_transformation.color_recommendations = results['recommendations']['colors']

                        # Save analysis images
                        hair_analysis_file = processor.pil_to_django_file(
                            results['images']['hair_analysis'], 
                            f"{session_id_local}_hair_analysis.png"
                        )
                        hair_transformation.hair_analysis_image.save(
                            f"{session_id_local}_hair_analysis.png", 
                            hair_analysis_file
                        )

                        face_analysis_file = processor.pil_to_django_file(
                            results['images']['face_analysis'], 
                            f"{session_id_local}_face_analysis.png"
                        )
                        hair_transformation.face_analysis_image.save(
                            f"{session_id_local}_face_analysis.png", 
                            face_analysis_file
                        )

                        hair_transformation.save()

                        # Save transformation results
                        for transformation in results['images']['transformations']:
                            transformed_file = processor.pil_to_django_file(
                                transformation['image'],
                                f"{session_id_local}_{transformation['style_type']}_{uuid.uuid4().hex[:8]}.png"
                            )

                            TransformationResult.objects.create(
                                hair_transformation=hair_transformation,
                                style_name=transformation['title'],
                                style_type=transformation['style_type'],
                                transformed_image=transformed_file
                            )

                except Exception as e:
                    # Log exception to console for now; in production use logging
                    print(f"Background processing error for {session_id_local}: {e}")
                finally:
                    # Remove lock file when done
                    try:
                        if os.path.exists(lock_path):
                            os.remove(lock_path)
                    except Exception:
                        pass

            # If lock file not present, create it and start background processing
            if not os.path.exists(lock_path):
                open(lock_path, 'w').close()
                t = threading.Thread(target=background_process, args=(session_id,))
                t.daemon = True
                t.start()

            # Render processing page which will poll the ajax endpoint
            return render(request, 'hair_transformation/processing.html', {
                'session_id': session_id,
                'original_image_url': hair_transformation.original_image.url
            })

        except HairTransformation.DoesNotExist:
            return render(request, 'hair_transformation/error.html', {
                'error': 'Session not found.'
            })

class ResultsView(View):
    def get(self, request, session_id):
        try:
            hair_transformation = HairTransformation.objects.get(session_id=session_id)
            transformation_results = hair_transformation.results.all()
            
            # Separate long and short styles
            long_styles = transformation_results.filter(style_type='Long')
            short_styles = transformation_results.filter(style_type='Short')
            
            context = {
                'transformation': hair_transformation,
                'long_styles': long_styles,
                'short_styles': short_styles,
                'analysis_data': {
                    'skin_tone': hair_transformation.skin_tone,
                    'ethnicity': hair_transformation.ethnicity,
                    'face_shape': hair_transformation.face_shape,
                    'hair_length': hair_transformation.hair_length,
                    'hair_texture': hair_transformation.hair_texture,
                }
            }
            
            return render(request, 'hair_transformation/results.html', context)
            
        except HairTransformation.DoesNotExist:
            return render(request, 'hair_transformation/error.html', {
                'error': 'Results not found.'
            })

class AjaxProcessingView(View):
    def get(self, request, session_id):
        """AJAX endpoint to check processing status"""
        try:
            hair_transformation = HairTransformation.objects.get(session_id=session_id)
            results_exist = hair_transformation.results.exists()
            
            return JsonResponse({
                'processed': results_exist,
                'status': 'complete' if results_exist else 'processing'
            })
        except HairTransformation.DoesNotExist:
            return JsonResponse({'error': 'Session not found'}, status=404)