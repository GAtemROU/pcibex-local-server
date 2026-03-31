import { Component, EventEmitter, Input, Output} from '@angular/core';
import { ApiService } from '../api.service';
import { ToastService } from '../toast.service';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-common-overlay',
  imports: [CommonModule],
  templateUrl: './common-overlay.component.html',
  styleUrl: './common-overlay.component.css'
})

export class CommonOverlayComponent{
   @Output() closed = new EventEmitter<void>();
   @Input() actionType!: string | null;
    @Input() selectedItem!: any; 

   constructor(private apiService: ApiService, private toastService: ToastService) {
    console.log(this.toastService)
   }

   ngOnInit() {
  console.log('Received in child:', this.actionType, this.selectedItem);
}

   close() {
    this.closed.emit();
  }

  async executeAction() {
    switch(this.actionType) {
      case 'erase':
      await this.eraseResults(); break;
      case 'delete':
        await this.deleteExperiment(); break;
    }
  }

  async eraseResults(): Promise<void>{
    try {
      console.log('apiService:', this.apiService);
      const response = await this.apiService.eraseExperimentResults(this.selectedItem._id);
       if (response.message) {
      this.toastService.showSuccess(response.message);
    } else {
      this.toastService.showError(response.error || 'Failed to erase the experiment');
    }
          this.close();
    } catch (error: any) {
      let errorMessage = error?.error?.error || 'An unexpected error occured while erasing the experiment results. Please try again later'
      console.log(error)
      this.toastService.showError(errorMessage);
    }
  }

  async deleteExperiment(): Promise<void>{
    try {
      const response = await this.apiService.deleteExperiment(this.selectedItem._id);
       if (response.message) {
      this.toastService.showSuccess(response.message);
    } else {
      this.toastService.showError(response.error || 'Failed to delete the experiment');
    }
          this.close();
    } catch (error: any) {
      let errorMessage = error?.error?.error || 'An unexpected error occured while deleting the experiment results. Please try again later'
      this.toastService.showError(errorMessage);
    }
  }
}
