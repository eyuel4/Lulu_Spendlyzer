import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { ReactiveFormsModule, FormBuilder, FormGroup, FormArray, Validators } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../services/auth.service';
import { trigger, state, style, transition, animate } from '@angular/animations';

interface Question {
  id: string;
  text: string;
  type: 'radio' | 'checkbox' | 'text';
  options?: { value: string; label: string; description?: string }[];
  required: boolean;
  placeholder?: string;
}

interface UserPreferences {
  account_type: 'personal' | 'family';
  primary_goal: string[];
  financial_focus: string[];
  experience_level: 'beginner' | 'intermediate' | 'advanced';
}

@Component({
  selector: 'app-questionnaire',
  standalone: true,
  templateUrl: './questionnaire.component.html',
  styleUrls: ['./questionnaire.component.scss'],
  imports: [ReactiveFormsModule, CommonModule],
  animations: [
    trigger('slideAnimation', [
      transition(':enter', [
        style({ transform: 'translateX(100%)', opacity: 0 }),
        animate('300ms ease-out', style({ transform: 'translateX(0)', opacity: 1 }))
      ]),
      transition('* => left', [
        style({ transform: 'translateX(-100%)', opacity: 0 }),
        animate('300ms ease-out', style({ transform: 'translateX(0)', opacity: 1 }))
      ]),
      transition('* => right', [
        style({ transform: 'translateX(100%)', opacity: 0 }),
        animate('300ms ease-out', style({ transform: 'translateX(0)', opacity: 1 }))
      ])
    ])
  ]
})
export class QuestionnaireComponent implements OnInit {
  questionnaireForm: FormGroup;
  currentQuestionIndex = 0;
  loading = false;
  slideDirection: 'left' | 'right' = 'left';
  Math = Math; // Make Math available in template
  showIconBounce = false; // Control icon bounce animation

  questions: Question[] = [
    {
      id: 'account_type',
      text: 'How do you plan to use Spendlyzer?',
      type: 'radio',
      required: true,
      options: [
        {
          value: 'personal',
          label: 'Personal Finance',
          description: 'Just for me - track my own spending and savings'
        },
        {
          value: 'family',
          label: 'Family/Household',
          description: 'Manage finances for my family or household'
        }
      ]
    },
    {
      id: 'primary_goal',
      text: 'What\'s your primary financial goal?',
      type: 'checkbox',
      required: true,
      options: [
        { value: 'emergency_fund', label: 'Build emergency fund' },
        { value: 'debt_payoff', label: 'Pay off debt' },
        { value: 'savings', label: 'Save for big purchases' },
        { value: 'budgeting', label: 'Better budgeting' },
        { value: 'investment', label: 'Investment planning' },
        { value: 'retirement', label: 'Retirement planning' }
      ]
    },
    {
      id: 'financial_focus',
      text: 'What would you like to focus on most?',
      type: 'checkbox',
      required: true,
      options: [
        { value: 'expense_tracking', label: 'Track daily expenses' },
        { value: 'category_analysis', label: 'Analyze spending categories' },
        { value: 'budget_planning', label: 'Create and stick to budgets' },
        { value: 'savings_goals', label: 'Set and achieve savings goals' },
        { value: 'financial_reports', label: 'Detailed financial reports' },
        { value: 'bill_reminders', label: 'Bill payment reminders' }
      ]
    },
    {
      id: 'experience_level',
      text: 'How would you describe your financial management experience?',
      type: 'radio',
      required: true,
      options: [
        {
          value: 'beginner',
          label: 'Beginner',
          description: 'Just starting to manage finances seriously'
        },
        {
          value: 'intermediate',
          label: 'Intermediate',
          description: 'Have some experience with budgeting and tracking'
        },
        {
          value: 'advanced',
          label: 'Advanced',
          description: 'Experienced with detailed financial planning'
        }
      ]
    }
  ];

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router
  ) {
    this.questionnaireForm = this.fb.group({});
  }

  ngOnInit(): void {
    this.initializeForm();
    this.triggerIconBounce();
  }

  private initializeForm(): void {
    const formControls: { [key: string]: any } = {};
    
    this.questions.forEach(question => {
      if (question.type === 'checkbox') {
        formControls[question.id] = [[]]; // Initialize with empty array
      } else {
        formControls[question.id] = ['', question.required ? Validators.required : null];
      }
    });

    this.questionnaireForm = this.fb.group(formControls);
  }

  private triggerIconBounce(): void {
    this.showIconBounce = true;
    setTimeout(() => {
      this.showIconBounce = false;
    }, 1000); // Stop bounce after 1 second
  }

  get currentQuestion(): Question {
    return this.questions[this.currentQuestionIndex];
  }

  get progressPercentage(): number {
    return ((this.currentQuestionIndex + 1) / this.questions.length) * 100;
  }

  get isFirstQuestion(): boolean {
    return this.currentQuestionIndex === 0;
  }

  get isLastQuestion(): boolean {
    return this.currentQuestionIndex === this.questions.length - 1;
  }

  onOptionSelect(questionId: string, value: string, isCheckbox: boolean = false): void {
    if (isCheckbox) {
      const control = this.questionnaireForm.get(questionId);
      if (control) {
        const currentValues = control.value as string[] || [];
        const index = currentValues.indexOf(value);
        
        if (index > -1) {
          currentValues.splice(index, 1);
        } else {
          currentValues.push(value);
        }
        
        control.setValue(currentValues);
      }
    } else {
      this.questionnaireForm.get(questionId)?.setValue(value);
    }
  }

  isOptionSelected(questionId: string, value: string): boolean {
    const control = this.questionnaireForm.get(questionId);
    if (!control) return false;

    if (this.currentQuestion.type === 'checkbox') {
      const values = control.value as string[] || [];
      return values.includes(value);
    } else {
      return control.value === value;
    }
  }

  canProceed(): boolean {
    const currentControl = this.questionnaireForm.get(this.currentQuestion.id);
    if (!currentControl) return false;

    if (this.currentQuestion.type === 'checkbox') {
      const values = currentControl.value as string[];
      return values && values.length > 0;
    } else {
      return currentControl.valid && currentControl.value;
    }
  }

  nextQuestion(): void {
    if (this.canProceed()) {
      this.slideDirection = 'left';
      this.currentQuestionIndex++;
      this.triggerIconBounce();
    }
  }

  previousQuestion(): void {
    this.slideDirection = 'right';
    this.currentQuestionIndex--;
    this.triggerIconBounce();
  }

  async submitQuestionnaire(): Promise<void> {
    if (this.questionnaireForm.valid) {
      this.loading = true;
      
      try {
        const preferences: UserPreferences = {
          account_type: this.questionnaireForm.get('account_type')?.value,
          primary_goal: this.questionnaireForm.get('primary_goal')?.value || [],
          financial_focus: this.questionnaireForm.get('financial_focus')?.value || [],
          experience_level: this.questionnaireForm.get('experience_level')?.value
        };

        // Save preferences to backend
        await this.authService.saveUserPreferences(preferences).toPromise();
        
        // Navigate based on account type
        if (preferences.account_type === 'family') {
          this.router.navigate(['/family-setup']);
        } else {
          this.router.navigate(['/dashboard']);
        }
      } catch (error) {
        console.error('Error saving preferences:', error);
        // Fallback to dashboard
        this.router.navigate(['/dashboard']);
      } finally {
        this.loading = false;
      }
    }
  }

  skipQuestionnaire(): void {
    if (typeof window !== 'undefined' && window.localStorage) {
      localStorage.setItem('questionnaire_skipped', 'true');
    }
    this.router.navigate(['/dashboard']);
  }
} 