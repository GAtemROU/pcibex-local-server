import { Injectable } from '@angular/core';
import { Toast } from 'bootstrap';
import { DOCUMENT } from '@angular/common';
import { PLATFORM_ID, Inject} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

@Injectable({
  providedIn: 'root',
})
export class ToastService {

  private isBrowser: boolean;
  constructor(@Inject(DOCUMENT) private document: Document, @Inject(PLATFORM_ID) private platformId: object) {
    this.isBrowser = isPlatformBrowser(this.platformId);
  }
  
  private showToast(type: string, message: string, title: string): void {
    if (isPlatformBrowser(this.platformId)) {
      setTimeout(() => {
        const toastEl = document.getElementById(`${type}Toast`);
        const toastBody = document.getElementById(`${type}ToastMessage`);

        if (toastEl && toastBody) {
          toastBody.textContent = message;

          // Use Renderer2 to trigger the Bootstrap toast display
          // @ts-ignore (to avoid TypeScript errors with bootstrap)
          const bsToast = new bootstrap.Toast(toastEl);
          bsToast.show();
        }
      });
    }
  }

  showError(message: string): void {
    this.showToast('error', message, 'Error');
  }

  showSuccess(message: string): void {
    this.showToast('success', message, 'Success');
  }

  showInfo(message: string): void {
    this.showToast('info', message, 'Info');
  }
}
