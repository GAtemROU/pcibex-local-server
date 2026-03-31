import { Component, EventEmitter, Output } from '@angular/core';
import { ApiService } from '../api.service';
import { ToastService } from '../toast.service';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-create-user',
  imports: [CommonModule, FormsModule],
  templateUrl: './create-user.component.html',
  styleUrl: './create-user.component.css'
})
export class CreateUserComponent {
@Output() closed = new EventEmitter<void>();

 formData = {
    full_name: '',
    username: '',
    role: ""
  };

   clearForm() {
    this.formData = {
      full_name: '',
      username: '',
      role:''
    };
  }



  constructor(private apiService: ApiService, private toastService: ToastService) {}

  close() {
    this.closed.emit();
  }

  async onSubmit(form: any) {
    if (form.valid) {
      await this.createUser()
    }
  }

  async createUser(): Promise<void> {
  try {
    const createdExperiment = await this.apiService.createUser(this.formData);
    if (createdExperiment.message) {
      this.toastService.showSuccess(createdExperiment.message);
      this.clearForm();
      this.close();
    } else {
      this.toastService.showError(createdExperiment.error || 'Failed  to create the experiment');
    }
  } catch (error:any) {
    let errorMessage = error?.error?.error || 'An unexpected error occured while creating the experiment. Please try again later'
    this.toastService.showError(errorMessage);
  }
}
}
