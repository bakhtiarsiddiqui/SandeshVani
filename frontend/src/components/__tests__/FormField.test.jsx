import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import FormField from '../ui/FormField';
import Input from '../ui/Input';

describe('FormField component', () => {
  it('renders label and connects to input via htmlFor and id', () => {
    render(
      <FormField label="Campaign Title" id="title" required>
        {({ id }) => <Input id={id} />}
      </FormField>
    );

    expect(screen.getByLabelText(/campaign title/i)).toBeInTheDocument();
    expect(screen.getByText('*')).toHaveAttribute('aria-hidden', 'true');
  });

  it('renders error message with alert role and links via aria-describedby', () => {
    render(
      <FormField
        label="Recipient Email"
        id="email"
        error="Please provide a valid email"
      >
        {({ id, 'aria-describedby': describedBy, hasError }) => (
          <Input id={id} aria-describedby={describedBy} hasError={hasError} />
        )}
      </FormField>
    );

    const input = screen.getByLabelText(/recipient email/i);
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input).toHaveAttribute('aria-describedby', 'email-error');
    expect(screen.getByRole('alert')).toHaveTextContent(/please provide a valid email/i);
  });
});

