import React from "react"
import {
  Drawer,
  Box,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemButton,
  Typography,
  Divider,
  IconButton,
} from "@mui/material"
import CloseIcon from "@mui/icons-material/Close"
import ViewQuiltIcon from "@mui/icons-material/ViewQuilt"
import DashboardIcon from "@mui/icons-material/Dashboard"
import AttachMoneyIcon from "@mui/icons-material/AttachMoney"
import FormatQuoteIcon from "@mui/icons-material/FormatQuote"
import ContactMailIcon from "@mui/icons-material/ContactMail"
import ViewAgendaIcon from "@mui/icons-material/ViewAgenda"
import PhotoLibraryIcon from "@mui/icons-material/PhotoLibrary"
import CampaignIcon from "@mui/icons-material/Campaign"
import GroupIcon from "@mui/icons-material/Group"
import QuestionAnswerIcon from "@mui/icons-material/QuestionAnswer"
import { SECTION_TYPES, SECTION_CATEGORIES, SectionTypeDefinition } from "./sectionTypes"

interface SectionLibraryProps {
  open: boolean
  onClose: () => void
  onAddSection: (sectionType: string) => void
}

const iconMap: Record<string, React.ReactElement> = {
  ViewQuilt: <ViewQuiltIcon />,
  Dashboard: <DashboardIcon />,
  AttachMoney: <AttachMoneyIcon />,
  FormatQuote: <FormatQuoteIcon />,
  ContactMail: <ContactMailIcon />,
  ViewAgenda: <ViewAgendaIcon />,
  PhotoLibrary: <PhotoLibraryIcon />,
  Campaign: <CampaignIcon />,
  Group: <GroupIcon />,
  QuestionAnswer: <QuestionAnswerIcon />,
}

const getIconForSection = (iconName: string): React.ReactElement => {
  return iconMap[iconName] || <DashboardIcon />
}

const SectionLibrary: React.FC<SectionLibraryProps> = ({ open, onClose, onAddSection }) => {
  const getSectionsByCategory = (category: string): SectionTypeDefinition[] => {
    return SECTION_TYPES.filter((section) => section.category === category)
  }

  return (
    <Drawer
      anchor="left"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: {
          width: 320,
          backgroundColor: "#fafafa",
        },
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          p: 2,
          borderBottom: "1px solid #e0e0e0",
          backgroundColor: "#ffffff",
        }}
      >
        <Typography variant="h6" fontWeight="bold">
          Section Library
        </Typography>
        <IconButton size="small" onClick={onClose}>
          <CloseIcon />
        </IconButton>
      </Box>

      {/* Description */}
      <Box sx={{ px: 2, py: 1.5 }}>
        <Typography variant="body2" color="text.secondary">
          Click a section type to add it to your page.
        </Typography>
      </Box>

      {/* Section list grouped by category */}
      <Box sx={{ flex: 1, overflow: "auto" }}>
        {SECTION_CATEGORIES.map((category) => {
          const sections = getSectionsByCategory(category)
          if (sections.length === 0) return null

          return (
            <Box key={category}>
              <Box sx={{ px: 2, pt: 2, pb: 0.5 }}>
                <Typography
                  variant="overline"
                  color="text.secondary"
                  fontWeight={600}
                  letterSpacing={1}
                >
                  {category}
                </Typography>
              </Box>
              <List dense disablePadding>
                {sections.map((section) => (
                  <ListItem key={section.type} disablePadding>
                    <ListItemButton
                      onClick={() => onAddSection(section.type)}
                      sx={{
                        px: 2,
                        py: 1,
                        "&:hover": {
                          backgroundColor: "#e3f2fd",
                        },
                      }}
                    >
                      <ListItemIcon sx={{ minWidth: 40, color: "#1976d2" }}>
                        {getIconForSection(section.icon)}
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Typography variant="body2" fontWeight={500}>
                            {section.label}
                          </Typography>
                        }
                        secondary={
                          <Typography variant="caption" color="text.secondary">
                            {section.description}
                          </Typography>
                        }
                      />
                    </ListItemButton>
                  </ListItem>
                ))}
              </List>
              <Divider sx={{ mt: 1 }} />
            </Box>
          )
        })}
      </Box>
    </Drawer>
  )
}

export default SectionLibrary
