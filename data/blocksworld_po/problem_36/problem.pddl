(define (problem blocksworld)
	(:domain blocksworld)
	(:objects
		blue - block
		green - block
		orange - block
		purple - block
		red - block
		yellow - block
		robot - robot
	)
	(:init (handempty robot)
		(ontable purple)
		(on red purple)
		(clear red)
		(ontable green)
		(clear green)
		(ontable orange)
		(clear orange)

		(ontable blue)
		(on yellow blue)
		(clear yellow)
	)
	(:goal (and (handempty robot)
		(ontable purple)
		(on blue purple)
		(clear blue)
		(ontable red)
		(on orange red)
		(clear orange)

		(ontable yellow)
		(on green yellow)
		(clear green)
	))
)