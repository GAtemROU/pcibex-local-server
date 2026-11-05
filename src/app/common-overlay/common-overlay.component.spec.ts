import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

import { CommonOverlayComponent } from './common-overlay.component';

describe('CommonOverlayComponent', () => {
  let component: CommonOverlayComponent;
  let fixture: ComponentFixture<CommonOverlayComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CommonOverlayComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    })
    .compileComponents();

    fixture = TestBed.createComponent(CommonOverlayComponent);
    component = fixture.componentInstance;
    component.selectedItem = { experiment: 'test experiment' };
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
