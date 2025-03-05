// frontend/components/SandboxCard.tsx
import React from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';

interface Sandbox {
  id: number;
  name: string;
  status: string;
}

interface SandboxCardProps {
  sandbox: Sandbox;
}

export default function SandboxCard({ sandbox }: SandboxCardProps) {
  return (
    <Card className="shadow hover:shadow-lg transition duration-200">
      <CardContent>
        <Typography variant="h5" component="div">
          {sandbox.name}
        </Typography>
        <Typography color="text.secondary">
          Status: {sandbox.status}
        </Typography>
      </CardContent>
    </Card>
  );
}
