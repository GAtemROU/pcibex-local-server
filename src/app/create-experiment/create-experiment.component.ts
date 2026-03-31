import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../api.service';
import { ToastService } from '../toast.service';

@Component({
  selector: 'app-create-experiment',
  imports: [CommonModule, FormsModule],
  templateUrl: './create-experiment.component.html',
  styleUrl: './create-experiment.component.css'
})
export class CreateExperimentComponent {
 @Output() closed = new EventEmitter<void>();

  formData = {
    name: '',
    tags: '',
    redirect_url: ''
  };


  constructor(private apiService: ApiService, private toastService: ToastService) {}

  close() {
    this.closed.emit();
  }

  async onSubmit(form: any) {
    if (form.valid &&  this.uploadedFile) {
      await this.createExperiment()
    }
  }

  async createExperiment(): Promise<void> {
  try {
    const formDataToSubmit = new FormData();
      formDataToSubmit.append('name', this.formData.name);
      formDataToSubmit.append('tags', this.formData.tags);
      formDataToSubmit.append('redirect_url', this.formData.redirect_url);
      
      if (this.uploadedFile) {
        formDataToSubmit.append('file', this.uploadedFile);
    }
    
    const createdExperiment = await this.apiService.createExperiment(formDataToSubmit);
    if (createdExperiment.message) {
      this.toastService.showSuccess(createdExperiment.message);
      this.clearForm();
      this.close();
    } else {
      this.toastService.showError(createdExperiment.error || 'Failed  to create the experiment');
    }
  } catch (error:any) {
    console.log(error)
    let errorMessage = error?.error?.error || 'An unexpected error occured while creating the experiment. Please try again later'
    this.toastService.showError(errorMessage);
  }
}

  clearForm() {
    this.formData = {
      name: '',
      tags: '',
      redirect_url: ''
    };
    this.uploadedFile = null;
    this.fileError = '';
    this.isFileInputTouched = false;
  }

 uploadedFile: File | null = null;
  isDragging = false;
  fileError = '';
  isFileInputTouched = false;

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = false;
    this.isFileInputTouched = true;

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.handleFile(files[0]);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.handleFile(input.files[0]);
    }
  }

  handleFile(file: File): void {
    this.fileError = '';

    // Validate file type
    if (!file.name.toLowerCase().endsWith('.zip')) {
      this.fileError = 'Only ZIP files are allowed.';
      return;
    }

    const maxSize = 20 * 1024 * 1024; // 20MB
    if (file.size > maxSize) {
      this.fileError = 'File size must not exceed 20MB.';
      return;
    }

    this.uploadedFile = file;
  }

  removeFile(event: Event): void {
    event.stopPropagation();
    this.uploadedFile = null;
    this.fileError = '';
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  }

}
