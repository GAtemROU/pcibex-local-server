import { Component, Renderer2, Inject } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { CommonModule, DOCUMENT } from '@angular/common';
import { ToastService } from '../toast.service';
import { ApiService } from '../api.service';
import { CreateExperimentComponent } from '../create-experiment/create-experiment.component';
import { AuthService } from '../auth.service';
import { CommonOverlayComponent } from "../common-overlay/common-overlay.component";
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-landing',
  imports: [CommonModule, CreateExperimentComponent, CommonOverlayComponent, FormsModule],
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.css'
})

export class LandingComponent {
  items: any[] = []; // Your raw data
  filterMode: 'all' | 'mine' = 'all';
  filteredItems: any[] = [];
  groupedItems: { [key: string]: any[] } = {};
  collapseStates: { [key: string]: boolean } = {};

  constructor( private http: HttpClient,
    private authService: AuthService,
    private toastService: ToastService,
    private apiService: ApiService,
    @Inject(DOCUMENT) private document: Document) {}
  errorMessage: string | null = null;
  searchTerm: string = '';

  ngOnInit() {
    this.loadExperiments();
  }

  onSearchChange() {
  this.loadItems();
}

  async loadItems(): Promise<void> {
    try{
    const { items } = await this.apiService.getExperimentsBasedOnSearch(this.searchTerm);
    this.items = items;
    this.filterItems()
  } catch (error) {
    console.error('Failed to load experiments:', error);
  }
}

  setFilterMode(mode: 'all' | 'mine', event: Event) {
  event.preventDefault(); // Prevents anchor scroll
  this.filterMode = mode;
  this.filterItems();
}

filterItems() {
  const userId = this.authService.getUserId(); 
  this.filteredItems =
    this.filterMode === 'mine'
      ? this.items.filter(item => item.created_by === userId)
      : [...this.items];

  this.groupItemsByMonth(this.filteredItems);
}


  showOverlay = false;
  toggleOverlay() {
    this.showOverlay = !this.showOverlay;
  }

  closeOverlay() {
    this.showOverlay = false;
    this.ngOnInit();
  }

  showCommonOverlay = false;
  selectedItem = null;
  overlayMode: 'erase' | 'delete' | null = null;

  openCommonOverlay(mode: 'erase' | 'delete', experiment: any) {
    this.overlayMode = mode;
    this.selectedItem = experiment;
    console.log(experiment, this.overlayMode)
    this.showCommonOverlay = true;
  }

  closeCommonOverlay() {
    this.showCommonOverlay = false;
    this.overlayMode = null;
  }


async loadExperiments(): Promise<void> {
  try {
    const { items } = await this.apiService.getExperiments();
    this.items = items;
    this.filterItems()
  } catch (error) {
    console.error('Failed to load experiments:', error);
  }
}

  groupItemsByMonth(items: any[]) {
    this.groupedItems = items.reduce((acc, item) => {
      const date = new Date(item.last_edited);
      const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      if (!acc[key]) acc[key] = [];
      acc[key].push(item);
      return acc;
    }, {} as { [key: string]: any[] });

    this.collapseStates = {};
    for (const key of Object.keys(this.groupedItems)) {
      this.collapseStates[key] = true; // Open by default
    }
  }

  toggleCollapse(key: string): void {
    this.collapseStates[key] = !this.collapseStates[key];
  }

  clipboardState: string | null = null; // Temporary state

  copyToClipboard(link: string, event: Event) {
    navigator.clipboard.writeText(link).then(() => {
      this.clipboardState = link;
      setTimeout(() => {
        if (this.clipboardState === link) {
          this.clipboardState = null;
        }
      }, 2000); // Reset text after 2 seconds
    }).catch(err => {
      this.toastService.showError('Failed to copy link to clipboard');
    });
  
    event.stopPropagation();
  }
   
  sortByDateDesc = (a: any, b: any) => {
    return a.key < b.key ? 1 : -1;
  };

  async downloadSource(experimentId: string) {
    try {
    const res = await this.apiService.downloadExperimentSource(experimentId);

    // Try to extract filename from Content-Disposition
    let filename = `${experimentId}_source.zip`;
    const contentDisposition = res.headers.get('Content-Disposition');
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="?([^"]+)"?/);
      if (match && match[1]) {
        filename = match[1];
      }
    }

    const blob = res.body as Blob;
    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(blobUrl);

  } catch (err) {
    this.toastService.showError('Failed to download source code zip file');
  }
  }

async downloadResults(experimentId: string) {
  try {
    const res = await this.apiService.downloadExperimentResults(experimentId);

    // Try to extract filename from Content-Disposition
    let filename = `${experimentId}_results.csv`;
    const contentDisposition = res.headers.get('Content-Disposition');
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="?([^"]+)"?/);
      if (match && match[1]) {
        filename = match[1];
      }
    }

    const blob = res.body as Blob;
    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(blobUrl);

  } catch (err) {
    this.toastService.showError('Failed to download results');
  }
}

}

