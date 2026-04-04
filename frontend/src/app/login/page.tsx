'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { createClient } from '@/lib/supabase/client'
import { Logo } from '@/components/ui/Logo'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Suspense } from 'react'

const loginSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Please enter a valid email'),
  password: z.string().min(1, 'Password is required'),
})

type LoginFormData = z.infer<typeof loginSchema>

function LoginForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const callbackError = searchParams.get('error')

  const [showResendConfirmation, setShowResendConfirmation] = useState(false)
  const [resending, setResending] = useState(false)
  const [resendSuccess, setResendSuccess] = useState(false)
  const [lastEmail, setLastEmail] = useState('')

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = async (data: LoginFormData) => {
    setShowResendConfirmation(false)
    setResendSuccess(false)

    const supabase = createClient()
    const { data: authData, error } = await supabase.auth.signInWithPassword({
      email: data.email,
      password: data.password,
    })

    if (error) {
      setError('root', { message: 'Invalid email or password. Please try again.' })
      return
    }

    // Enforce email confirmation
    if (authData.user && !authData.user.email_confirmed_at) {
      await supabase.auth.signOut()
      setLastEmail(data.email)
      setShowResendConfirmation(true)
      setError('root', {
        message: 'Please verify your email address before signing in. Check your inbox for a confirmation link.',
      })
      return
    }

    router.push('/dashboard')
    router.refresh()
  }

  const handleResendConfirmation = async () => {
    setResending(true)
    setResendSuccess(false)
    const supabase = createClient()
    const { error } = await supabase.auth.resend({
      type: 'signup',
      email: lastEmail,
    })
    if (error) {
      setError('root', { message: 'Failed to resend confirmation email. Please try again.' })
    } else {
      setResendSuccess(true)
    }
    setResending(false)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-[400px]">
        {/* Logo */}
        <div className="text-center mb-8 flex justify-center">
          <Logo size="lg" />
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-xl text-slate-900">Welcome back</CardTitle>
            <CardDescription>Sign in to your account to continue.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {/* Callback error from auth flow */}
              {callbackError === 'auth_callback_failed' && (
                <div className="rounded-lg bg-rose-50 border border-rose-200 p-3 text-sm text-rose-700">
                  Authentication failed. Please try again.
                </div>
              )}

              {/* Form-level error (wrong credentials, unconfirmed email) */}
              {errors.root && (
                <div className="rounded-lg bg-rose-50 border border-rose-200 p-3 text-sm text-rose-700">
                  {errors.root.message}
                </div>
              )}

              {/* Resend confirmation email */}
              {showResendConfirmation && (
                <div className="rounded-lg bg-slate-50 border border-slate-200 p-3 space-y-2">
                  {resendSuccess ? (
                    <p className="text-sm text-emerald-700">
                      Confirmation email sent! Check your inbox and spam folder.
                    </p>
                  ) : (
                    <>
                      <p className="text-xs text-slate-500">Didn&apos;t receive the email?</p>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={handleResendConfirmation}
                        disabled={resending}
                        className="w-full"
                      >
                        {resending ? 'Sending...' : 'Resend Confirmation Email'}
                      </Button>
                    </>
                  )}
                </div>
              )}

              <div className="space-y-1.5">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@agency.com"
                  autoComplete="email"
                  {...register('email')}
                  aria-invalid={!!errors.email}
                />
                {errors.email && (
                  <p className="text-xs text-rose-600">{errors.email.message}</p>
                )}
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password">Password</Label>
                  <Link
                    href="/forgot-password"
                    className="text-sm text-indigo-600 hover:text-indigo-500"
                  >
                    Forgot password?
                  </Link>
                </div>
                <Input
                  id="password"
                  type="password"
                  placeholder="Your password"
                  autoComplete="current-password"
                  {...register('password')}
                  aria-invalid={!!errors.password}
                />
                {errors.password && (
                  <p className="text-xs text-rose-600">{errors.password.message}</p>
                )}
              </div>

              <Button
                type="submit"
                className="w-full bg-indigo-700 hover:bg-indigo-800 text-white"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Signing in\u2026' : 'Sign In'}
              </Button>
            </form>

            <p className="mt-4 text-center text-sm text-slate-500">
              Don&apos;t have an account?{' '}
              <Link href="/signup" className="text-indigo-700 hover:underline font-medium">
                Sign up
              </Link>
            </p>
            <p className="mt-3 text-center text-xs text-slate-400">
              <Link href="/terms" className="hover:underline">Terms</Link>
              {' \u00B7 '}
              <Link href="/privacy" className="hover:underline">Privacy</Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

// Wrap in Suspense because useSearchParams() requires it in Next.js App Router
export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  )
}
